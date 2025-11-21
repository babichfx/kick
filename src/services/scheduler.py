"""
Scheduler Service.
Manages per-user reminder scheduling using APScheduler with persistent SQLite job store.

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
from typing import Optional
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.jobstores.sqlalchemy import SQLAlchemyJobStore
from apscheduler.triggers.cron import CronTrigger
import pytz

from config import DATABASE_PATH, BotPhrases
import database as db

logger = logging.getLogger(__name__)

# Global scheduler instance
scheduler: Optional[AsyncIOScheduler] = None

# Global bot application reference (cannot be pickled, so stored separately)
_bot_application = None


def init_scheduler():
    """
    Initialize APScheduler with SQLite-based persistent job store.

    Jobs persist across bot restarts. Call this once at bot startup.
    """
    global scheduler

    # Create job store using SQLite for persistence
    jobstores = {
        'default': SQLAlchemyJobStore(url=f'sqlite:///{DATABASE_PATH.parent / "scheduler.db"}')
    }

    # Use UTC for scheduler internal time
    scheduler = AsyncIOScheduler(jobstores=jobstores, timezone=pytz.utc)
    scheduler.start()

    logger.info("Scheduler initialized with persistent job store")
    logger.info(f"Job store location: {DATABASE_PATH.parent / 'scheduler.db'}")


def set_bot_application(application):
    """
    Set the bot application reference for sending reminders.

    Must be called after init_scheduler() and before scheduling any reminders.
    The bot application cannot be pickled, so we store it separately from job args.

    Args:
        application: The Telegram bot Application instance
    """
    global _bot_application
    _bot_application = application
    logger.info("Bot application reference set for scheduler")


async def schedule_user_reminders(telegram_user_id: int):
    """
    Schedule reminders for a user based on their saved schedule.

    Removes any existing jobs for this user and creates new ones.
    Jobs are created from the user's reminder_schedule in the database.

    Args:
        telegram_user_id: Telegram user ID

    Example schedule from database:
        {
            "times": ["09:00", "13:00", "17:00", "21:00"],
            "day_filter": "weekdays",
            "timezone": "Europe/Moscow"
        }
    """
    if not scheduler:
        logger.error("Scheduler not initialized")
        return

    # Remove existing jobs for this user first
    remove_user_reminders(telegram_user_id)

    # Get user's schedule from database
    schedule = db.get_reminder_schedule(telegram_user_id)
    if not schedule:
        logger.warning(f"No schedule found for user {telegram_user_id}")
        return

    times = schedule['times']
    day_filter = schedule['day_filter']
    timezone_str = schedule['timezone']

    try:
        timezone = pytz.timezone(timezone_str)
    except pytz.exceptions.UnknownTimeZoneError:
        logger.error(f"Unknown timezone: {timezone_str}")
        return

    # Create a job for each scheduled time
    for time_str in times:
        try:
            hour, minute = map(int, time_str.split(':'))

            # Create cron trigger based on day_filter
            if day_filter == 'weekdays':
                # Monday(0) to Friday(4)
                trigger = CronTrigger(
                    hour=hour,
                    minute=minute,
                    day_of_week='0-4',
                    timezone=timezone
                )
            elif day_filter == 'weekends':
                # Saturday(5), Sunday(6)
                trigger = CronTrigger(
                    hour=hour,
                    minute=minute,
                    day_of_week='5-6',
                    timezone=timezone
                )
            else:  # 'all'
                # Every day
                trigger = CronTrigger(
                    hour=hour,
                    minute=minute,
                    timezone=timezone
                )

            # Create unique job ID
            job_id = f"reminder_{telegram_user_id}_{time_str}"

            # Add job to scheduler
            # NOTE: Only pass telegram_user_id (picklable), not bot (unpicklable)
            scheduler.add_job(
                send_reminder,
                trigger=trigger,
                args=[telegram_user_id],
                id=job_id,
                replace_existing=True
            )

            logger.info(f"Scheduled reminder for user {telegram_user_id} at {time_str} ({day_filter})")

        except Exception as e:
            logger.error(f"Error scheduling time {time_str} for user {telegram_user_id}: {e}")

    logger.info(f"Successfully scheduled {len(times)} reminders for user {telegram_user_id}")


def remove_user_reminders(telegram_user_id: int):
    """
    Remove all scheduled reminders for a user.

    Call this when user wants to change their schedule or disable reminders.

    Args:
        telegram_user_id: Telegram user ID
    """
    if not scheduler:
        logger.error("Scheduler not initialized")
        return

    jobs = scheduler.get_jobs()
    removed_count = 0

    for job in jobs:
        if job.id.startswith(f"reminder_{telegram_user_id}_"):
            job.remove()
            removed_count += 1

    logger.info(f"Removed {removed_count} reminders for user {telegram_user_id}")


async def send_reminder(telegram_user_id: int):
    """
    Send reminder message to user with inline keyboard buttons.

    This function fires at scheduled times. Sends the reminder prompt
    with two options:
    - "Да, пошагово" - Step-by-step guided practice
    - "Нет" - Dismiss (records refusal)

    Args:
        telegram_user_id: Telegram user ID
    """
    from telegram import InlineKeyboardButton, InlineKeyboardMarkup

    if not _bot_application:
        logger.error("Bot application not set - cannot send reminder")
        return

    try:
        # Create inline keyboard with two buttons
        keyboard = [
            [InlineKeyboardButton(BotPhrases.BTN_YES_GUIDED, callback_data='reminder_yes_guided')],
            [InlineKeyboardButton(BotPhrases.BTN_NO, callback_data='reminder_no')]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        # Send reminder message using the bot from the application
        await _bot_application.bot.send_message(
            chat_id=telegram_user_id,
            text=BotPhrases.REMINDER_PROMPT,  # "Готов записать наблюдение?"
            reply_markup=reply_markup
        )

        logger.info(f"Sent reminder to user {telegram_user_id}")

    except Exception as e:
        logger.error(f"Error sending reminder to user {telegram_user_id}: {e}")


def get_user_jobs(telegram_user_id: int) -> list:
    """
    Get all scheduled jobs for a user.

    Useful for debugging or showing user their active reminders.

    Args:
        telegram_user_id: Telegram user ID

    Returns:
        List of job objects for this user
    """
    if not scheduler:
        logger.error("Scheduler not initialized")
        return []

    jobs = scheduler.get_jobs()
    user_jobs = [job for job in jobs if job.id.startswith(f"reminder_{telegram_user_id}_")]

    return user_jobs


def shutdown_scheduler():
    """
    Shutdown scheduler gracefully.

    Call this when bot is shutting down. Jobs are persisted to database
    and will be restored on next startup.
    """
    global scheduler

    if scheduler:
        scheduler.shutdown(wait=True)
        logger.info("Scheduler shut down gracefully")
        scheduler = None
