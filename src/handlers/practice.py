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
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes

from config import BotPhrases, PRACTICE_FIELDS
import database as db

logger = logging.getLogger(__name__)


async def handle_practice_input(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
    """
    Handle user input during guided practice.

    This function is called from the main message handler when user is in guided_practice mode.
    It collects the user's answer and shows confirmation button.
    User can send multiple messages to add more - they accumulate automatically.

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

    # Store or append to current answer
    if context.user_data.get('current_answer') is None:
        # First answer for this field
        context.user_data['current_answer'] = user_text
    else:
        # User is adding more - append to existing answer
        context.user_data['current_answer'] += "\n" + user_text

    # Show the accumulated answer with confirmation button and explanation
    keyboard = [
        [InlineKeyboardButton(BotPhrases.BTN_OK, callback_data='field_ok')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    confirmation_text = f"{context.user_data['current_answer']}\n\nПодтвердите ответ или добавьте что-то если необходимо."
    await update.message.reply_text(confirmation_text, reply_markup=reply_markup)

    logger.info(f"User {user_id} answered field '{current_field['name']}', awaiting confirmation")

    return True


async def handle_practice_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Handle callback queries during guided practice.

    Handles callback type:
    - field_ok: Accept current answer and move to next field
    """
    query = update.callback_query
    await query.answer()

    user_id = update.effective_user.id
    callback_data = query.data

    # Check if user is in guided practice mode
    if context.user_data.get('mode') != 'guided_practice':
        return

    try:
        if callback_data == 'field_ok':
            # User confirmed the answer - save it and move to next field
            current_field_idx = context.user_data.get('current_field', 0)

            if current_field_idx >= len(PRACTICE_FIELDS):
                logger.error(f"Invalid field index {current_field_idx} for user {user_id}")
                return

            current_field = PRACTICE_FIELDS[current_field_idx]
            current_answer = context.user_data.get('current_answer', '')

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
                await query.message.reply_text(next_field['prompt'])

                logger.info(f"User {user_id} moved to field '{next_field['name']}'")

            else:
                # All fields completed - save to database
                await complete_practice(update, context, query.message)

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
            entry_type='structured_practice',
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

        # Confirm to user
        await message.reply_text(BotPhrases.PRACTICE_SAVED)

        logger.info(f"User {user_id} completed practice, entry ID: {entry_id}")

    except Exception as e:
        logger.error(f"Error completing practice for user {user_id}: {e}", exc_info=True)
        await message.reply_text("Ошибка при сохранении записи. Попробуйте еще раз.")
