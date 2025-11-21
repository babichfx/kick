"""
Authentication handler for Kick bot.
Implements password-based authentication for all users.

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
from telegram.ext import ContextTypes

from config import BOT_PASSWORD, BotPhrases
from database import (
    ensure_user_exists,
    is_user_authenticated,
    update_user_auth,
    update_user_activity
)

logger = logging.getLogger(__name__)


async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Handle /start command.
    If user is not authenticated, request password.
    If authenticated, show main menu or welcome message.
    """
    user_id = update.effective_user.id

    # Ensure user exists in database
    ensure_user_exists(user_id)

    # Check if user is authenticated
    if is_user_authenticated(user_id):
        # User is already authenticated
        update_user_activity(user_id)
        await update.message.reply_text("Бот готов к работе.")
        logger.info(f"User {user_id} started bot (already authenticated)")
    else:
        # Request password
        context.user_data['awaiting_password'] = True
        await update.message.reply_text(BotPhrases.AUTH_REQUEST)
        logger.info(f"User {user_id} started bot (awaiting password)")


async def check_password(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
    """
    Check if user is trying to authenticate with password.
    Returns True if password check was performed (successful or not).
    Returns False if this is not a password attempt.
    """
    user_id = update.effective_user.id

    # Check if we're waiting for password from this user
    if not context.user_data.get('awaiting_password', False):
        return False

    # Get the message text
    password_attempt = update.message.text.strip()

    # Check password
    if password_attempt == BOT_PASSWORD:
        # Authentication successful
        update_user_auth(user_id, True)
        context.user_data['authenticated'] = True
        context.user_data['awaiting_password'] = False
        await update.message.reply_text(BotPhrases.AUTH_SUCCESS)
        logger.info(f"User {user_id} authenticated successfully")
        return True
    else:
        # Authentication failed
        await update.message.reply_text(BotPhrases.AUTH_FAILED)
        logger.warning(f"User {user_id} failed authentication")
        return True


async def require_auth(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
    """
    Gate function to check if user is authenticated.
    Returns True if authenticated, False otherwise.
    Should be called at the beginning of protected handlers.
    """
    user_id = update.effective_user.id

    # Check both database and context for authentication
    db_authenticated = is_user_authenticated(user_id)
    context_authenticated = context.user_data.get('authenticated', False)

    if db_authenticated:
        # Sync context with database state
        context.user_data['authenticated'] = True
        update_user_activity(user_id)
        return True

    if context_authenticated:
        # Sync database with context state (edge case)
        update_user_auth(user_id, True)
        update_user_activity(user_id)
        return True

    # User not authenticated
    await update.message.reply_text(BotPhrases.AUTH_REQUEST)
    context.user_data['awaiting_password'] = True
    return False
