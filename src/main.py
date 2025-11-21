"""
Kick Bot - Mindfulness and Awareness Practice Bot
Main entry point for the Telegram bot.

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
from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    filters,
)

from config import TELEGRAM_BOT_TOKEN
from database import init_database

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)


def main() -> None:
    """
    Initialize and run the bot.
    """
    logger.info("Starting Kick bot")

    # Initialize database
    init_database()

    # Build application
    application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()

    # Import handlers (imported here to avoid circular imports)
    from handlers.auth import start_command, check_password

    # Register command handlers
    application.add_handler(CommandHandler('start', start_command))

    # Text message handler (for password authentication and future features)
    async def handle_text(update: Update, context) -> None:
        """Route text messages to appropriate handlers."""
        # First check if this is a password attempt
        if await check_password(update, context):
            return

        # TODO: Add more text message handling here:
        # - Reminder schedule configuration
        # - Practice entry input
        # - Diary entry input

        # For now, just acknowledge the message for authenticated users
        from handlers.auth import require_auth
        if await require_auth(update, context):
            logger.info(f"Message from user {update.effective_user.id}: {update.message.text[:50]}")

    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))

    # TODO: Add more handlers as we implement them:
    # - Voice message handlers
    # - Callback query handlers for inline buttons
    # - Reminder response handlers

    # Start polling
    logger.info("Bot started polling...")
    application.run_polling(
        poll_interval=2.0,
        timeout=30,
        drop_pending_updates=True,
        allowed_updates=Update.ALL_TYPES
    )


if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        logger.info("Bot stopped by user")
    except Exception as e:
        logger.error(f"Bot crashed: {e}", exc_info=True)
