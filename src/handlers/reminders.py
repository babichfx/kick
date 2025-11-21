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

    # Check if user has timezone set
    user_timezone = db.get_user_timezone(user_id)

    # If no timezone set (or default), ask user to confirm or set timezone
    if not user_timezone or user_timezone == 'Europe/Moscow':
        # Ask for timezone with common options
        keyboard = [
            [InlineKeyboardButton("UTC+0 — Лондон, Лиссабон, Касабланка",
                                  callback_data="tz_Europe/London")],
            [InlineKeyboardButton("UTC+1 — Берлин, Париж, Рим, Мадрид",
                                  callback_data="tz_Europe/Berlin")],
            [InlineKeyboardButton("UTC+2 — Киев, Каир, Калининград",
                                  callback_data="tz_Europe/Kyiv")],
            [InlineKeyboardButton("UTC+3 — Москва, Стамбул, Найроби",
                                  callback_data="tz_Europe/Moscow")],
            [InlineKeyboardButton("UTC+4 — Дубай, Баку, Самара, Ереван",
                                  callback_data="tz_Asia/Dubai")],
            [InlineKeyboardButton("UTC+5 — Екатеринбург, Ташкент, Карачи",
                                  callback_data="tz_Asia/Tashkent")],
            [InlineKeyboardButton("UTC+5:30 — Нью-Дели, Мумбаи, Калькутта",
                                  callback_data="tz_Asia/Kolkata")],
            [InlineKeyboardButton("UTC+6 — Алматы, Дакка, Бишкек, Омск",
                                  callback_data="tz_Asia/Almaty")],
            [InlineKeyboardButton("UTC+6:30 — Янгон, Нейпьидо, Мандалай",
                                  callback_data="tz_Asia/Yangon")],
            [InlineKeyboardButton("UTC+7 — Новосибирск, Бангкок, Джакарта",
                                  callback_data="tz_Asia/Bangkok")],
            [InlineKeyboardButton("UTC+8 — Иркутск, Гонконг, Сингапур",
                                  callback_data="tz_Asia/Shanghai")],
            [InlineKeyboardButton("UTC+9 — Якутск, Токио, Сеул",
                                  callback_data="tz_Asia/Tokyo")],
            [InlineKeyboardButton("UTC+9:30 — Аделаида, Дарвин",
                                  callback_data="tz_Australia/Adelaide")],
            [InlineKeyboardButton("UTC+10 — Владивосток, Сидней, Мельбурн",
                                  callback_data="tz_Australia/Sydney")],
            [InlineKeyboardButton("UTC+10:30 — остров Лорд-Хау",
                                  callback_data="tz_Australia/Lord_Howe")],
            [InlineKeyboardButton("UTC+11 — Магадан, Сахалин, Нумеа",
                                  callback_data="tz_Asia/Magadan")],
            [InlineKeyboardButton("UTC+12 — Петропавловск-Камчатский, Анадырь",
                                  callback_data="tz_Pacific/Auckland")],
            [InlineKeyboardButton("UTC+13 — Токелау, Нукуалофа, Апиа",
                                  callback_data="tz_Pacific/Tongatapu")],
            [InlineKeyboardButton("UTC+14 — Киритимати (Остров Рождества)",
                                  callback_data="tz_Pacific/Kiritimati")],
            [InlineKeyboardButton("Другой часовой пояс",
                                  callback_data="tz_custom")],
        ]

        reply_markup = InlineKeyboardMarkup(keyboard)

        context.user_data['setting_timezone'] = True

        await update.message.reply_text(
            "В каком часовом поясе вы находитесь?",
            reply_markup=reply_markup
        )
        logger.info(f"User {user_id} asked for timezone selection")
        return

    # Set state to await schedule input
    context.user_data['awaiting_schedule'] = True

    await update.message.reply_text(BotPhrases.REMINDER_REQUEST)
    logger.info(f"User {user_id} started schedule configuration")


async def handle_schedule_input(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
    """
    Handle natural language schedule input from user (text or voice).

    Called from main message handler when awaiting_schedule flag is set.
    Parses the schedule, saves it, and registers jobs with scheduler.

    Returns:
        True if schedule input was handled, False otherwise
    """
    user_id = update.effective_user.id

    # Check if we're waiting for schedule input
    if not context.user_data.get('awaiting_schedule', False):
        return False

    # Handle voice messages
    if update.message.voice:
        from services.transcription import transcribe_voice

        logger.info(f"User {user_id} sent voice message for schedule")

        # Get file URL
        voice_file = await context.bot.get_file(update.message.voice.file_id)
        file_url = voice_file.file_path

        # Transcribe
        schedule_text = await transcribe_voice(file_url, language="ru")

        if not schedule_text:
            await update.message.reply_text(
                "Не удалось распознать голосовое сообщение. Попробуйте еще раз."
            )
            return True

        # Show transcription with verification buttons
        keyboard = [
            [InlineKeyboardButton("Подтвердить", callback_data='schedule_confirm')],
            [InlineKeyboardButton("Отменить", callback_data='schedule_cancel')]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        # Store transcription for later use
        context.user_data['transcribed_schedule'] = schedule_text

        await update.message.reply_text(
            f"Распознано: {schedule_text}",
            reply_markup=reply_markup
        )

        logger.info(f"Transcribed schedule for user {user_id}: {schedule_text}")
        return True

    # Handle text messages
    schedule_text = update.message.text.strip()

    logger.info(f"User {user_id} sent schedule request: {schedule_text}")

    try:
        # Get user timezone
        user_timezone = db.get_user_timezone(user_id)

        # Parse schedule using GPT with user's timezone
        schedule = await parse_schedule(schedule_text, user_timezone)

        if not schedule:
            await update.message.reply_text(
                "Не удалось распознать расписание. Попробуйте еще раз."
            )
            logger.warning(f"Failed to parse schedule for user {user_id}: {schedule_text}")
            return True

        # Save schedule to database (synchronous, commits immediately)
        db.set_reminder_schedule(user_id, schedule)

        # IMPORTANT: Small delay to ensure database commit completes
        # before scheduler reads the schedule. This prevents race condition
        # where scheduler tries to read before write transaction commits.
        import asyncio
        await asyncio.sleep(0.1)

        # Schedule reminders with scheduler service
        await scheduler.schedule_user_reminders(user_id)

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


async def handle_schedule_verification(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Handle callback queries from schedule transcription verification buttons.

    Handles two callback types:
    - schedule_confirm: Proceed with parsing transcribed schedule
    - schedule_cancel: Cancel and return to schedule input prompt
    """
    query = update.callback_query
    await query.answer()

    user_id = update.effective_user.id
    callback_data = query.data

    logger.info(f"User {user_id} responded to schedule verification: {callback_data}")

    try:
        if callback_data == 'schedule_confirm':
            # Get transcribed schedule from user_data
            schedule_text = context.user_data.get('transcribed_schedule')

            if not schedule_text:
                await query.message.edit_text("Ошибка: текст расписания не найден.")
                context.user_data['awaiting_schedule'] = False
                return

            # Delete verification message
            await query.message.delete()

            # Get user timezone
            user_timezone = db.get_user_timezone(user_id)

            # Parse schedule using GPT with user's timezone
            schedule = await parse_schedule(schedule_text, user_timezone)

            if not schedule:
                await query.message.reply_text(
                    "Не удалось распознать расписание. Попробуйте еще раз."
                )
                logger.warning(f"Failed to parse schedule for user {user_id}: {schedule_text}")
                context.user_data['transcribed_schedule'] = None
                return

            # Save schedule to database
            db.set_reminder_schedule(user_id, schedule)

            # IMPORTANT: Small delay to ensure database commit completes
            import asyncio
            await asyncio.sleep(0.1)

            # Schedule reminders with scheduler service
            await scheduler.schedule_user_reminders(user_id)

            # Clear state
            context.user_data['awaiting_schedule'] = False
            context.user_data['transcribed_schedule'] = None

            # Confirm to user
            times_str = ", ".join(schedule['times'])
            day_filter_str = {
                'weekdays': 'по будням',
                'weekends': 'по выходным',
                'all': 'каждый день'
            }.get(schedule.get('day_filter', 'all'), 'каждый день')

            confirmation = f"{BotPhrases.REMINDER_CONFIGURED}\nВремя: {times_str}\nДни: {day_filter_str}"
            await context.bot.send_message(chat_id=user_id, text=confirmation)

            logger.info(f"Successfully configured schedule for user {user_id}: {schedule}")

        elif callback_data == 'schedule_cancel':
            # User cancelled - delete verification message and prompt again
            await query.message.delete()
            context.user_data['transcribed_schedule'] = None

            await context.bot.send_message(
                chat_id=user_id,
                text=BotPhrases.REMINDER_REQUEST
            )

            logger.info(f"User {user_id} cancelled schedule transcription")

    except Exception as e:
        logger.error(f"Error handling schedule verification for user {user_id}: {e}", exc_info=True)
        await context.bot.send_message(
            chat_id=user_id,
            text="Произошла ошибка при настройке расписания. Попробуйте еще раз."
        )
        context.user_data['awaiting_schedule'] = False
        context.user_data['transcribed_schedule'] = None


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

    Handles two callback types:
    - reminder_yes_guided: Start guided step-by-step practice
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
            context.user_data['current_answer'] = None  # Track current answer being refined

            # Delete reminder message
            await query.message.delete()

            # Send prompt for first field (content)
            from config import PRACTICE_FIELDS
            from handlers.practice import send_field_prompt
            first_field = PRACTICE_FIELDS[0]

            await send_field_prompt(query.message, first_field, 0)

            logger.info(f"User {user_id} started guided practice")

        elif callback_data == 'reminder_no':
            # User declined - record refusal
            db.create_refusal(user_id)

            # Delete reminder message
            await query.message.delete()

            logger.info(f"User {user_id} declined reminder")

    except Exception as e:
        logger.error(f"Error handling reminder response for user {user_id}: {e}", exc_info=True)
        await query.message.reply_text("Произошла ошибка. Попробуйте еще раз.")


async def handle_timezone_selection(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Handle callback queries from timezone selection buttons.

    Handles timezone selection and custom timezone input.
    """
    query = update.callback_query
    await query.answer()

    user_id = update.effective_user.id
    callback_data = query.data

    logger.info(f"User {user_id} selected timezone: {callback_data}")

    try:
        if callback_data.startswith('tz_') and callback_data != 'tz_custom':
            # Extract timezone from callback data
            timezone = callback_data[3:]  # Remove 'tz_' prefix

            # Validate timezone using pytz
            import pytz
            try:
                pytz.timezone(timezone)
            except pytz.exceptions.UnknownTimeZoneError:
                await query.message.edit_text(
                    f"Неверный часовой пояс: {timezone}. Попробуйте еще раз."
                )
                context.user_data['setting_timezone'] = False
                return

            # Save timezone to database
            db.set_user_timezone(user_id, timezone)

            # Delete timezone selection message
            await query.message.delete()

            # Clear timezone setting flag and start schedule input
            context.user_data['setting_timezone'] = False
            context.user_data['awaiting_schedule'] = True

            # Prompt for schedule
            await context.bot.send_message(
                chat_id=user_id,
                text=f"Часовой пояс установлен: {timezone}\n\n{BotPhrases.REMINDER_REQUEST}"
            )

            logger.info(f"User {user_id} set timezone to {timezone}")

        elif callback_data == 'tz_custom':
            # User wants to enter custom timezone
            await query.message.edit_text(
                "Отправьте название часового пояса в формате 'Region/City' (например, 'Europe/Paris', 'Asia/Tokyo').\n\n"
                "Список доступных часовых поясов: https://en.wikipedia.org/wiki/List_of_tz_database_time_zones"
            )

            # Set flag to await custom timezone input
            context.user_data['awaiting_custom_timezone'] = True
            context.user_data['setting_timezone'] = False

            logger.info(f"User {user_id} requested custom timezone input")

    except Exception as e:
        logger.error(f"Error handling timezone selection for user {user_id}: {e}", exc_info=True)
        await context.bot.send_message(
            chat_id=user_id,
            text="Произошла ошибка при установке часового пояса. Попробуйте еще раз."
        )
        context.user_data['setting_timezone'] = False


async def handle_custom_timezone_input(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
    """
    Handle custom timezone input from user.

    Called from main message handler when awaiting_custom_timezone flag is set.

    Returns:
        True if custom timezone input was handled, False otherwise
    """
    user_id = update.effective_user.id

    # Check if we're waiting for custom timezone input
    if not context.user_data.get('awaiting_custom_timezone', False):
        return False

    timezone = update.message.text.strip()

    logger.info(f"User {user_id} sent custom timezone: {timezone}")

    # Validate timezone using pytz
    import pytz
    try:
        pytz.timezone(timezone)
    except pytz.exceptions.UnknownTimeZoneError:
        await update.message.reply_text(
            f"Неверный часовой пояс: {timezone}. Попробуйте еще раз или используйте /schedule для выбора из списка."
        )
        context.user_data['awaiting_custom_timezone'] = False
        return True

    # Save timezone to database
    db.set_user_timezone(user_id, timezone)

    # Clear flag and start schedule input
    context.user_data['awaiting_custom_timezone'] = False
    context.user_data['awaiting_schedule'] = True

    # Prompt for schedule
    await update.message.reply_text(
        f"Часовой пояс установлен: {timezone}\n\n{BotPhrases.REMINDER_REQUEST}"
    )

    logger.info(f"User {user_id} set custom timezone to {timezone}")
    return True
