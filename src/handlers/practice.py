"""
Guided Practice handler for Kick bot.
Handles step-by-step awareness practice with field-by-field collection.

Copyright (C) 2025 Vitaliy Babich

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program.  If not, see <https://www.gnu.org/licenses/>.
"""

import logging
import asyncio
from typing import Dict
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes

from config import BotPhrases, PRACTICE_FIELDS
import database as db

logger = logging.getLogger(__name__)

# Timer storage for message accumulation (per user, per field)
field_timers: Dict[int, any] = {}
field_message_parts: Dict[int, list] = {}


async def send_field_confirmation(update: Update, context: ContextTypes.DEFAULT_TYPE, user_id: int) -> None:
    """
    Send accumulated field message parts with confirmation button.

    Args:
        update: Telegram update
        context: Telegram context
        user_id: User ID
    """
    try:
        # Get accumulated message parts
        full_text = '\n'.join(field_message_parts[user_id])

        # Store in current_answer
        context.user_data['current_answer'] = full_text

        # Get current field info
        current_field_idx = context.user_data.get('current_field', 0)
        current_field = PRACTICE_FIELDS[current_field_idx]

        # Show confirmation button with back button if not on first field
        current_field_idx = context.user_data.get('current_field', 0)
        keyboard = []

        if current_field_idx > 0:
            # Add back and OK buttons side by side
            keyboard.append([
                InlineKeyboardButton("← Назад", callback_data='field_back'),
                InlineKeyboardButton(BotPhrases.BTN_OK, callback_data='field_ok')
            ])
        else:
            # Just OK button on first field
            keyboard.append([InlineKeyboardButton(BotPhrases.BTN_OK, callback_data='field_ok')])

        reply_markup = InlineKeyboardMarkup(keyboard)

        confirmation_text = f"{full_text}\n\nПодтвердите ответ или добавьте что-то если необходимо."

        # Send to chat
        chat_id = update.effective_chat.id
        await context.bot.send_message(
            chat_id=chat_id,
            text=confirmation_text,
            reply_markup=reply_markup
        )

        # Clean up
        del field_message_parts[user_id]
        del field_timers[user_id]

        logger.info(f"User {user_id} finished entering field '{current_field['name']}', awaiting confirmation")

    except KeyError:
        # Already cleaned up
        pass
    except Exception as e:
        logger.error(f"Error in send_field_confirmation: {e}", exc_info=True)


async def handle_practice_input(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
    """
    Handle user text input during guided practice.

    This function is called from the main message handler when user is in guided_practice mode.
    It collects the user's answer with 0.5 second buffering for multi-part messages.

    Returns:
        True if input was handled, False otherwise
    """
    # Check if user is in guided practice mode
    if context.user_data.get('mode') != 'guided_practice':
        return False

    user_id = update.effective_user.id
    user_text = update.message.text.strip()

    current_field_idx = context.user_data.get('current_field', 0)

    # Validate field index
    if current_field_idx >= len(PRACTICE_FIELDS):
        logger.error(f"Invalid field index {current_field_idx} for user {user_id}")
        context.user_data['mode'] = None
        return True

    current_field = PRACTICE_FIELDS[current_field_idx]

    # Initialize message parts list if first message for this field
    if user_id not in field_message_parts:
        field_message_parts[user_id] = []
        # If there's already a current_answer (user is adding more text after confirmation),
        # include it as the first part
        if context.user_data.get('current_answer'):
            field_message_parts[user_id].append(context.user_data['current_answer'])

    # Add message part
    field_message_parts[user_id].append(user_text)
    logger.debug(f"Accumulated message part for user {user_id}, field '{current_field['name']}', total parts: {len(field_message_parts[user_id])}")

    # Cancel existing timer if any
    if user_id in field_timers:
        field_timers[user_id].cancel()

    # Start new timer (0.5 seconds delay)
    loop = asyncio.get_event_loop()
    field_timers[user_id] = loop.call_later(
        0.5,
        asyncio.create_task,
        send_field_confirmation(update, context, user_id)
    )

    return True


async def handle_practice_voice(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
    """
    Handle user voice input during guided practice.

    Transcribes voice message and adds to message accumulator like text input.

    Returns:
        True if input was handled, False otherwise
    """
    # Check if user is in guided practice mode
    if context.user_data.get('mode') != 'guided_practice':
        return False

    user_id = update.effective_user.id

    current_field_idx = context.user_data.get('current_field', 0)

    # Validate field index
    if current_field_idx >= len(PRACTICE_FIELDS):
        logger.error(f"Invalid field index {current_field_idx} for user {user_id}")
        context.user_data['mode'] = None
        return True

    current_field = PRACTICE_FIELDS[current_field_idx]

    try:
        # Get voice file from Telegram
        voice = update.message.voice
        file = await context.bot.get_file(voice.file_id)
        file_url = file.file_path

        logger.info(f"User {user_id} sent voice message for field '{current_field['name']}', transcribing...")

        # Send typing indicator
        await update.message.chat.send_action("typing")

        # Transcribe voice
        from services.transcription import transcribe_voice
        transcribed_text = await transcribe_voice(file_url, language="ru")

        if not transcribed_text:
            await update.message.reply_text("Не удалось распознать голосовое сообщение. Попробуйте еще раз.")
            return True

        logger.info(f"Transcribed voice for user {user_id}: {transcribed_text[:100]}")

        # Show transcription to user
        await update.message.reply_text(f"Распознано: {transcribed_text}")

        # Initialize message parts list if first message for this field
        if user_id not in field_message_parts:
            field_message_parts[user_id] = []
            # If there's already a current_answer (user is adding more text after confirmation),
            # include it as the first part
            if context.user_data.get('current_answer'):
                field_message_parts[user_id].append(context.user_data['current_answer'])

        # Add transcribed text to message parts
        field_message_parts[user_id].append(transcribed_text)
        logger.debug(f"Accumulated transcribed voice for user {user_id}, field '{current_field['name']}', total parts: {len(field_message_parts[user_id])}")

        # Cancel existing timer if any
        if user_id in field_timers:
            field_timers[user_id].cancel()

        # Start new timer (0.5 seconds delay)
        loop = asyncio.get_event_loop()
        field_timers[user_id] = loop.call_later(
            0.5,
            asyncio.create_task,
            send_field_confirmation(update, context, user_id)
        )

        return True

    except Exception as e:
        logger.error(f"Error handling voice message for user {user_id}: {e}", exc_info=True)
        await update.message.reply_text("Ошибка при обработке голосового сообщения. Попробуйте еще раз.")
        return True


async def send_field_prompt(message, field, field_idx: int) -> None:
    """
    Send field prompt with optional inline buttons for form field.

    Args:
        message: Telegram message object to reply to
        field: Field configuration dict
        field_idx: Index of the current field
    """
    prompt_text = field['prompt']

    # Add form selection buttons for the form field (index 2)
    if field_idx == 2:  # form field
        keyboard = [
            [InlineKeyboardButton("Да-принимающее", callback_data='form_yes_accepting')],
            [InlineKeyboardButton("Нет-принимающее", callback_data='form_no_accepting')],
            [InlineKeyboardButton("Да-отрицающее", callback_data='form_yes_rejecting')],
            [InlineKeyboardButton("Нет-отрицающее", callback_data='form_no_rejecting')]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await message.reply_text(prompt_text, reply_markup=reply_markup)
    else:
        # Regular field - just send text prompt
        await message.reply_text(prompt_text)


async def handle_practice_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Handle callback queries during guided practice.

    Handles callback types:
    - field_ok: Accept current answer and move to next field
    - field_back: Go back to previous field
    - form_yes_accepting/form_no_accepting/form_yes_rejecting/form_no_rejecting: Form selection buttons
    """
    query = update.callback_query
    await query.answer()

    user_id = update.effective_user.id
    callback_data = query.data

    # Check if user is in guided practice mode
    if context.user_data.get('mode') != 'guided_practice':
        return

    try:
        # Handle form selection buttons
        if callback_data.startswith('form_'):
            current_field_idx = context.user_data.get('current_field', 0)

            # Map callback data to form text
            form_map = {
                'form_yes_accepting': 'Да-принимающее',
                'form_no_accepting': 'Нет-принимающее',
                'form_yes_rejecting': 'Да-отрицающее',
                'form_no_rejecting': 'Нет-отрицающее'
            }

            selected_form = form_map.get(callback_data, '')

            if not selected_form:
                logger.error(f"Unknown form callback: {callback_data}")
                return

            # Save the form selection
            context.user_data['practice_data']['form'] = selected_form
            context.user_data['current_answer'] = None

            # Delete the form selection message
            await query.message.delete()

            # Move to next field (body)
            next_field_idx = current_field_idx + 1
            context.user_data['current_field'] = next_field_idx
            next_field = PRACTICE_FIELDS[next_field_idx]

            # Send prompt for next field
            await send_field_prompt(query.message, next_field, next_field_idx)

            logger.info(f"User {user_id} selected form '{selected_form}', moved to field '{next_field['name']}'")
            return

        if callback_data == 'field_ok':
            # User confirmed the answer - save it and move to next field
            current_field_idx = context.user_data.get('current_field', 0)

            if current_field_idx >= len(PRACTICE_FIELDS):
                logger.error(f"Invalid field index {current_field_idx} for user {user_id}")
                return

            current_field = PRACTICE_FIELDS[current_field_idx]
            current_answer = context.user_data.get('current_answer', '')

            # Validate that answer is not empty
            if not current_answer or not current_answer.strip():
                await query.message.reply_text("Ответ не может быть пустым. Отправьте текст.")
                return

            # Save answer to practice_data
            context.user_data['practice_data'][current_field['name']] = current_answer
            context.user_data['current_answer'] = None  # Reset for next field

            # Delete the confirmation message
            await query.message.delete()

            # Move to next field or complete the practice
            next_field_idx = current_field_idx + 1

            if next_field_idx < len(PRACTICE_FIELDS):
                # More fields to go
                context.user_data['current_field'] = next_field_idx
                next_field = PRACTICE_FIELDS[next_field_idx]

                # Send prompt for next field
                await send_field_prompt(query.message, next_field, next_field_idx)

                logger.info(f"User {user_id} moved to field '{next_field['name']}'")

            else:
                # All fields completed - save to database
                await complete_practice(update, context, query.message)

        elif callback_data == 'field_back':
            # User wants to go back to previous field
            current_field_idx = context.user_data.get('current_field', 0)

            if current_field_idx <= 0:
                # Already on first field, can't go back
                await query.answer("Это первый шаг.")
                return

            # Cancel any pending timer for current field
            if user_id in field_timers:
                field_timers[user_id].cancel()
                del field_timers[user_id]
            if user_id in field_message_parts:
                del field_message_parts[user_id]

            # Delete the confirmation message
            await query.message.delete()

            # Move back one field
            prev_field_idx = current_field_idx - 1
            context.user_data['current_field'] = prev_field_idx
            prev_field = PRACTICE_FIELDS[prev_field_idx]

            # Get previously saved answer for this field
            prev_answer = context.user_data['practice_data'].get(prev_field['name'], '')

            # Set current answer to previous answer (user can keep it or replace it)
            context.user_data['current_answer'] = prev_answer

            # Show previous field with question prompt and previous answer
            if prev_answer:
                # Show question + previous answer + confirmation button
                keyboard = []
                if prev_field_idx > 0:
                    keyboard.append([
                        InlineKeyboardButton("← Назад", callback_data='field_back'),
                        InlineKeyboardButton(BotPhrases.BTN_OK, callback_data='field_ok')
                    ])
                else:
                    keyboard.append([InlineKeyboardButton(BotPhrases.BTN_OK, callback_data='field_ok')])

                reply_markup = InlineKeyboardMarkup(keyboard)
                # Include the question prompt so user remembers what they were answering
                message_text = f"{prev_field['prompt']}\n\n→ {prev_answer}\n\nОтправьте новый ответ или нажмите 'Всё ок' чтобы оставить предыдущий."
                await query.message.reply_text(message_text, reply_markup=reply_markup)
            else:
                # No previous answer, show prompt (with form buttons if form field)
                await send_field_prompt(query.message, prev_field, prev_field_idx)
                context.user_data['current_answer'] = None

            logger.info(f"User {user_id} went back to field '{prev_field['name']}'")

    except Exception as e:
        logger.error(f"Error handling practice callback for user {user_id}: {e}", exc_info=True)
        await query.message.reply_text("Произошла ошибка. Попробуйте еще раз.")


async def complete_practice(update: Update, context: ContextTypes.DEFAULT_TYPE, message) -> None:
    """
    Complete the practice session and save to database.

    Called when all fields have been collected.
    """
    user_id = update.effective_user.id
    practice_data = context.user_data.get('practice_data', {})

    try:
        # Create entry in database
        entry_id = db.create_entry(
            telegram_user_id=user_id,
            content=practice_data.get('content', ''),
            attitude=practice_data.get('attitude', ''),
            form=practice_data.get('form', ''),
            body=practice_data.get('body', ''),
            response=practice_data.get('response', '')
        )

        # Clear practice state
        context.user_data['mode'] = None
        context.user_data['current_field'] = None
        context.user_data['practice_data'] = {}
        context.user_data['current_answer'] = None

        # Clean up any pending timers
        if user_id in field_timers:
            field_timers[user_id].cancel()
            del field_timers[user_id]
        if user_id in field_message_parts:
            del field_message_parts[user_id]

        # Confirm to user
        await message.reply_text(BotPhrases.PRACTICE_SAVED)

        logger.info(f"User {user_id} completed practice, entry ID: {entry_id}")

    except Exception as e:
        logger.error(f"Error completing practice for user {user_id}: {e}", exc_info=True)
        await message.reply_text("Ошибка при сохранении записи. Попробуйте еще раз.")
