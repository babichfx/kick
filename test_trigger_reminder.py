#!/usr/bin/env python3
"""
Test script to manually trigger a reminder for a specific user.
Useful for testing the complete reminder → practice → save flow without waiting for scheduled times.

Copyright (C) 2025 Vitaliy Babich

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.
"""

import asyncio
import sys
import os

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from telegram import Bot
from config import TELEGRAM_BOT_TOKEN
from services.scheduler import send_reminder


async def main():
    """
    Send a test reminder to a specific user.

    Usage:
        python test_trigger_reminder.py <telegram_user_id>

    Example:
        python test_trigger_reminder.py 123456789
    """
    if len(sys.argv) < 2:
        print("Usage: python test_trigger_reminder.py <telegram_user_id>")
        print("")
        print("Example:")
        print("  python test_trigger_reminder.py 123456789")
        print("")
        print("This will send a test reminder message with buttons to the specified user.")
        sys.exit(1)

    try:
        user_id = int(sys.argv[1])
    except ValueError:
        print(f"Error: '{sys.argv[1]}' is not a valid user ID (must be an integer)")
        sys.exit(1)

    bot = Bot(TELEGRAM_BOT_TOKEN)

    print(f"Sending test reminder to user {user_id}...")
    try:
        await send_reminder(user_id, bot)
        print("✓ Reminder sent successfully!")
        print("")
        print("Check Telegram for the reminder message with buttons:")
        print("  - Да, пошагово (start guided practice)")
        print("  - Нет (dismiss and record refusal)")
    except Exception as e:
        print(f"✗ Error sending reminder: {e}")
        sys.exit(1)


if __name__ == '__main__':
    asyncio.run(main())
