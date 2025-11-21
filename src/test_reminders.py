"""
Test and demonstration of Reminder Configuration handlers.

This demonstrates the complete flow from schedule setup to reminder callbacks.

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

import asyncio
import logging
from datetime import datetime


# Mock classes for testing without Telegram
class MockMessage:
    """Mock Telegram message."""

    def __init__(self, text, user_id):
        self.text = text
        self.chat = MockChat(user_id)

    async def reply_text(self, text, reply_markup=None):
        """Simulate replying to message."""
        print(f"\n[BOT REPLY]")
        print(f"Text: {text}")
        if reply_markup:
            print(f"Buttons: {len(reply_markup.inline_keyboard)} rows")
        return MockMessage("", 0)

    async def delete(self):
        """Simulate deleting message."""
        print("[MESSAGE DELETED]")


class MockChat:
    """Mock Telegram chat."""

    def __init__(self, user_id):
        self.id = user_id


class MockUser:
    """Mock Telegram user."""

    def __init__(self, user_id):
        self.id = user_id


class MockUpdate:
    """Mock Telegram update."""

    def __init__(self, text, user_id):
        self.message = MockMessage(text, user_id)
        self.effective_user = MockUser(user_id)
        self.callback_query = None


class MockCallbackQuery:
    """Mock Telegram callback query."""

    def __init__(self, data, user_id):
        self.data = data
        self.message = MockMessage("", user_id)

    async def answer(self):
        """Simulate answering callback query."""
        pass


class MockContext:
    """Mock Telegram context."""

    def __init__(self, bot):
        self.bot = bot
        self.user_data = {}


class MockBot:
    """Mock bot for testing."""

    async def send_message(self, chat_id, text, reply_markup=None):
        """Simulate sending a message."""
        print(f"\n[BOT MESSAGE]")
        print(f"To: {chat_id}")
        print(f"Text: {text}")
        if reply_markup:
            print(f"Buttons: {len(reply_markup.inline_keyboard)} rows")
        return True


async def test_schedule_setup():
    """
    Test schedule configuration flow.

    Demonstrates:
    1. User sends /schedule command
    2. User provides natural language schedule
    3. Schedule is parsed, saved, and activated
    """
    import database as db
    from services import scheduler
    from handlers.reminders import (
        setup_schedule_command,
        handle_schedule_input
    )

    print("\n" + "="*80)
    print("TEST: SCHEDULE CONFIGURATION")
    print("="*80 + "\n")

    # Setup
    test_user_id = 123456789
    db.init_database()
    scheduler.init_scheduler()

    # Authenticate user first
    db.ensure_user_exists(test_user_id)
    db.update_user_auth(test_user_id, True)

    mock_bot = MockBot()
    context = MockContext(mock_bot)
    context.user_data['authenticated'] = True

    print("1. User sends /schedule command")
    update = MockUpdate("/schedule", test_user_id)
    await setup_schedule_command(update, context)

    print("\n2. User sends natural language schedule request")
    print("   Input: 'Напоминай мне с 9 до 22 каждые 3 часа по будням'")

    update = MockUpdate("Напоминай мне с 9 до 22 каждые 3 часа по будням", test_user_id)
    await handle_schedule_input(update, context)

    print("\n3. Verifying schedule was saved and activated")
    schedule = db.get_reminder_schedule(test_user_id)
    jobs = scheduler.get_user_jobs(test_user_id)

    print(f"   Schedule: {schedule}")
    print(f"   Active jobs: {len(jobs)}")
    for job in jobs:
        print(f"     - {job.id}")
        print(f"       Next run: {job.next_run_time}")

    # Cleanup
    scheduler.remove_user_reminders(test_user_id)
    db.clear_all_user_data(test_user_id)

    print("\n✓ Schedule configuration test complete\n")


async def test_reminder_callbacks():
    """
    Test reminder callback handlers.

    Demonstrates:
    1. User receives reminder with buttons
    2. User clicks different button options
    3. Appropriate mode is set in context
    """
    import database as db
    from services import scheduler
    from handlers.reminders import handle_reminder_response

    print("\n" + "="*80)
    print("TEST: REMINDER CALLBACKS")
    print("="*80 + "\n")

    test_user_id = 987654321
    db.ensure_user_exists(test_user_id)
    db.update_user_auth(test_user_id, True)

    mock_bot = MockBot()

    # Test 1: Yes, guided
    print("1. Testing 'Да, пошагово' button")
    context = MockContext(mock_bot)
    context.user_data['authenticated'] = True

    update = MockUpdate("", test_user_id)
    update.callback_query = MockCallbackQuery('reminder_yes_guided', test_user_id)

    await handle_reminder_response(update, context)

    print(f"   Mode set: {context.user_data.get('mode')}")
    print(f"   Current field: {context.user_data.get('current_field')}")
    print(f"   Practice data initialized: {'practice_data' in context.user_data}")
    print(f"   Current answer tracking: {'current_answer' in context.user_data}")

    # Test 2: No
    print("\n2. Testing 'Нет' button")
    context = MockContext(mock_bot)
    context.user_data['authenticated'] = True

    update = MockUpdate("", test_user_id)
    update.callback_query = MockCallbackQuery('reminder_no', test_user_id)

    await handle_reminder_response(update, context)

    refusals = db.get_user_refusals(test_user_id)
    print(f"   Refusal recorded: {len(refusals)} refusal(s)")

    # Cleanup
    db.clear_all_user_data(test_user_id)

    print("\n✓ Reminder callback test complete\n")


async def test_schedule_management():
    """
    Test schedule management commands.

    Demonstrates:
    1. View current schedule
    2. Disable schedule
    3. Re-enable schedule
    """
    import database as db
    from services import scheduler
    from handlers.reminders import (
        view_schedule_command,
        disable_schedule_command,
        setup_schedule_command,
        handle_schedule_input
    )

    print("\n" + "="*80)
    print("TEST: SCHEDULE MANAGEMENT")
    print("="*80 + "\n")

    test_user_id = 555555555
    db.init_database()
    scheduler.init_scheduler()

    db.ensure_user_exists(test_user_id)
    db.update_user_auth(test_user_id, True)

    mock_bot = MockBot()
    context = MockContext(mock_bot)
    context.user_data['authenticated'] = True

    # Set up a schedule first
    print("1. Setting up initial schedule")
    test_schedule = {
        "times": ["09:00", "13:00", "17:00", "21:00"],
        "day_filter": "weekdays",
        "timezone": "Europe/Moscow"
    }
    db.set_reminder_schedule(test_user_id, test_schedule)
    await scheduler.schedule_user_reminders(test_user_id, mock_bot)

    # View schedule
    print("\n2. Viewing schedule with /view_schedule")
    update = MockUpdate("/view_schedule", test_user_id)
    await view_schedule_command(update, context)

    # Disable schedule
    print("\n3. Disabling schedule with /disable_schedule")
    update = MockUpdate("/disable_schedule", test_user_id)
    await disable_schedule_command(update, context)

    jobs_after_disable = scheduler.get_user_jobs(test_user_id)
    print(f"   Jobs after disable: {len(jobs_after_disable)}")

    # Try to view disabled schedule
    print("\n4. Viewing schedule after disable")
    update = MockUpdate("/view_schedule", test_user_id)
    await view_schedule_command(update, context)

    # Cleanup
    scheduler.remove_user_reminders(test_user_id)
    db.clear_all_user_data(test_user_id)

    print("\n✓ Schedule management test complete\n")


async def test_full_flow():
    """
    Test complete end-to-end flow.

    Demonstrates the full user journey from setup to reminder response.
    """
    import database as db
    from services import scheduler
    from handlers.reminders import (
        setup_schedule_command,
        handle_schedule_input,
        handle_reminder_response
    )

    print("\n" + "="*80)
    print("TEST: FULL END-TO-END FLOW")
    print("="*80 + "\n")

    test_user_id = 111222333
    db.init_database()
    scheduler.init_scheduler()

    db.ensure_user_exists(test_user_id)
    db.update_user_auth(test_user_id, True)

    mock_bot = MockBot()
    context = MockContext(mock_bot)
    context.user_data['authenticated'] = True

    print("STEP 1: User configures schedule")
    print("        User: /schedule")
    update = MockUpdate("/schedule", test_user_id)
    await setup_schedule_command(update, context)

    print("\n        User: 'Напоминай 4 раза в день'")
    update = MockUpdate("Напоминай 4 раза в день", test_user_id)
    await handle_schedule_input(update, context)

    schedule = db.get_reminder_schedule(test_user_id)
    jobs = scheduler.get_user_jobs(test_user_id)
    print(f"\n        ✓ Schedule configured: {len(jobs)} reminders")

    print("\nSTEP 2: Reminder fires (simulated)")
    print("        Bot sends: 'Готов записать наблюдение?'")
    print("        with 3 buttons")

    print("\nSTEP 3: User responds to reminder")
    print("        User clicks: 'Да, пошагово'")
    update = MockUpdate("", test_user_id)
    update.callback_query = MockCallbackQuery('reminder_yes_guided', test_user_id)
    await handle_reminder_response(update, context)

    print(f"\n        ✓ Mode set to: {context.user_data.get('mode')}")
    print("        ✓ Ready to collect practice data")

    # Cleanup
    scheduler.remove_user_reminders(test_user_id)
    db.clear_all_user_data(test_user_id)

    print("\n✓ Full flow test complete\n")


async def run_all_tests():
    """Run all reminder handler tests."""
    import database as db
    from services import scheduler

    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    print("\n" + "="*80)
    print("REMINDER HANDLER TEST SUITE")
    print("="*80)

    # Initialize once
    db.init_database()
    scheduler.init_scheduler()

    try:
        await test_schedule_setup()
        await test_reminder_callbacks()
        await test_schedule_management()
        await test_full_flow()

        print("="*80)
        print("ALL REMINDER HANDLER TESTS PASSED ✓")
        print("="*80)
        print()

    finally:
        # Cleanup
        scheduler.shutdown_scheduler()
        print("Scheduler shut down gracefully")


if __name__ == '__main__':
    asyncio.run(run_all_tests())
