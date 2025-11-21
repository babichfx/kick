"""
Reminder Configuration handler for Kick bot.
Handles schedule setup, reminder callbacks, and reminder management.

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

from config import BotPhrases
import database as db
from services import scheduler
from services.schedule_parser import parse_schedule
from handlers.auth import require_auth

logger = logging.getLogger(__name__)


async def setup_schedule_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Handle /schedule command - start schedule configuration flow.
    Prompts user to send their schedule in natural language.
    """
    # Check authentication
    if not await require_auth(update, context):
        return

    user_id = update.effective_user.id

    # Set state to await schedule input
    context.user_data['awaiting_schedule'] = True

    await update.message.reply_text(BotPhrases.REMINDER_REQUEST)
    logger.info(f"User {user_id} started schedule configuration")


async def handle_schedule_input(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
    """
    Handle natural language schedule input from user.

    Called from main message handler when awaiting_schedule flag is set.
    Parses the schedule, saves it, and registers jobs with scheduler.

    Returns:
        True if schedule input was handled, False otherwise
    """
    user_id = update.effective_user.id

    # Check if we're waiting for schedule input
    if not context.user_data.get('awaiting_schedule', False):
        return False

    # Get user's natural language schedule request
    schedule_text = update.message.text.strip()

    logger.info(f"User {user_id} sent schedule request: {schedule_text}")

    try:
        # Parse schedule using GPT
        schedule = await parse_schedule(schedule_text)

        if not schedule:
            await update.message.reply_text(
                "Не удалось распознать расписание. Попробуйте еще раз."
            )
            logger.warning(f"Failed to parse schedule for user {user_id}: {schedule_text}")
            return True

        # Save schedule to database
        db.set_reminder_schedule(user_id, schedule)

        # Schedule reminders with scheduler service
        await scheduler.schedule_user_reminders(user_id, context.bot)

        # Clear awaiting flag
        context.user_data['awaiting_schedule'] = False

        # Confirm to user
        times_str = ", ".join(schedule['times'])
        day_filter_str = {
            'weekdays': 'по будням',
            'weekends': 'по выходным',
            'all': 'каждый день'
        }.get(schedule.get('day_filter', 'all'), 'каждый день')

        confirmation = f"{BotPhrases.REMINDER_CONFIGURED}\nВремя: {times_str}\nДни: {day_filter_str}"
        await update.message.reply_text(confirmation)

        logger.info(f"Successfully configured schedule for user {user_id}: {schedule}")
        return True

    except Exception as e:
        logger.error(f"Error configuring schedule for user {user_id}: {e}", exc_info=True)
        await update.message.reply_text(
            "Произошла ошибка при настройке расписания. Попробуйте еще раз."
        )
        context.user_data['awaiting_schedule'] = False
        return True


async def view_schedule_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Handle /view_schedule command - show user's current schedule.
    """
    # Check authentication
    if not await require_auth(update, context):
        return

    user_id = update.effective_user.id

    # Get schedule from database
    schedule = db.get_reminder_schedule(user_id)

    if not schedule:
        await update.message.reply_text("У вас нет настроенного расписания.")
        return

    # Get scheduled jobs to show next reminder time
    jobs = scheduler.get_user_jobs(user_id)

    # Format schedule info
    times_str = ", ".join(schedule['times'])
    day_filter_str = {
        'weekdays': 'по будням',
        'weekends': 'по выходным',
        'all': 'каждый день'
    }.get(schedule.get('day_filter', 'all'), 'каждый день')

    message = f"Текущее расписание:\nВремя: {times_str}\nДни: {day_filter_str}"

    if jobs:
        # Find next scheduled reminder
        next_run = min(job.next_run_time for job in jobs if job.next_run_time)
        message += f"\n\nСледующее напоминание: {next_run.strftime('%Y-%m-%d %H:%M')}"

    await update.message.reply_text(message)
    logger.info(f"User {user_id} viewed their schedule")


async def disable_schedule_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Handle /disable_schedule command - disable all reminders for user.
    """
    # Check authentication
    if not await require_auth(update, context):
        return

    user_id = update.effective_user.id

    # Remove all scheduled jobs
    scheduler.remove_user_reminders(user_id)

    # Clear schedule from database
    db.set_reminder_schedule(user_id, None)

    await update.message.reply_text("Напоминания отключены.")
    logger.info(f"User {user_id} disabled their schedule")


async def handle_reminder_response(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Handle callback queries from reminder message buttons.

    Handles three callback types:
    - reminder_yes_guided: Start guided step-by-step practice
    - reminder_yes_free: Start free-form practice
    - reminder_no: Dismiss and record refusal
    """
    query = update.callback_query
    await query.answer()

    user_id = update.effective_user.id
    callback_data = query.data

    logger.info(f"User {user_id} responded to reminder: {callback_data}")

    try:
        if callback_data == 'reminder_yes_guided':
            # Start guided step-by-step practice
            context.user_data['mode'] = 'guided_practice'
            context.user_data['current_field'] = 0  # Start with first field
            context.user_data['practice_data'] = {}  # Initialize practice data storage

            # Delete reminder message
            await query.message.delete()

            # Send prompt for first field (content)
            from config import PRACTICE_FIELDS
            first_field = PRACTICE_FIELDS[0]
            await query.message.reply_text(first_field['prompt'])

            logger.info(f"User {user_id} started guided practice")

        elif callback_data == 'reminder_yes_free':
            # Start free-form practice
            context.user_data['mode'] = 'free_practice'
            context.user_data['practice_data'] = {}

            # Delete reminder message
            await query.message.delete()

            # Show all fields at once
            from config import PRACTICE_FIELDS
            fields_text = "\n\n".join([f['prompt'] for f in PRACTICE_FIELDS])
            await query.message.reply_text(f"{fields_text}\n\n{BotPhrases.PRACTICE_START}")

            logger.info(f"User {user_id} started free practice")

        elif callback_data == 'reminder_no':
            # User declined - record refusal
            db.create_refusal(user_id)

            # Delete reminder message
            await query.message.delete()

            logger.info(f"User {user_id} declined reminder")

    except Exception as e:
        logger.error(f"Error handling reminder response for user {user_id}: {e}", exc_info=True)
        await query.message.reply_text("Произошла ошибка. Попробуйте еще раз.")
