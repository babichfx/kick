"""
Test and demonstration of Scheduler Service.

This demonstrates how to use the scheduler service with APScheduler.
Note: This requires a bot instance to actually send messages.

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

import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

import asyncio
import logging
from datetime import datetime

from src import database as db
from src.services import scheduler


# Mock bot for testing (without actual Telegram connection)
class MockBot:
    """Mock bot for testing scheduler without Telegram connection."""

    async def send_message(self, chat_id, text, reply_markup=None):
        """Simulate sending a message."""
        print(f"\n[MOCK MESSAGE SENT]")
        print(f"To: {chat_id}")
        print(f"Text: {text}")
        if reply_markup:
            print(f"Buttons: {len(reply_markup.inline_keyboard)} rows")
        print(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        return True


async def test_scheduler():
    """
    Test scheduler service initialization and job scheduling.

    This test demonstrates:
    1. Initializing the scheduler
    2. Scheduling reminders for a test user
    3. Viewing scheduled jobs
    4. Removing scheduled jobs
    """
    # Setup logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    print("\n" + "="*80)
    print("TESTING SCHEDULER SERVICE")
    print("="*80 + "\n")

    # Test user
    test_user_id = 123456789

    # 1. Initialize database and scheduler
    print("1. Initializing database and scheduler...")
    db.init_database()
    scheduler.init_scheduler()
    print("   ✓ Initialized\n")

    # 2. Create test user with schedule
    print("2. Creating test user with reminder schedule...")
    db.ensure_user_exists(test_user_id)

    test_schedule = {
        "times": ["09:00", "13:00", "17:00", "21:00"],
        "day_filter": "weekdays",
        "timezone": "Europe/Moscow"
    }
    db.set_reminder_schedule(test_user_id, test_schedule)
    print(f"   ✓ Schedule saved: {test_schedule['times']}")
    print(f"   ✓ Day filter: {test_schedule['day_filter']}")
    print(f"   ✓ Timezone: {test_schedule['timezone']}\n")

    # 3. Schedule reminders for the user
    print("3. Scheduling reminders...")
    await scheduler.schedule_user_reminders(test_user_id)
    print("   ✓ Reminders scheduled\n")

    # 4. Get and display scheduled jobs
    print("4. Viewing scheduled jobs...")
    jobs = scheduler.get_user_jobs(test_user_id)
    print(f"   ✓ Total jobs: {len(jobs)}")
    for job in jobs:
        print(f"     - Job ID: {job.id}")
        print(f"       Next run: {job.next_run_time}")
        print(f"       Trigger: {job.trigger}")
    print()

    # 5. Test different schedules
    print("5. Testing different schedule types...\n")

    test_schedules = [
        {
            "name": "Weekends only",
            "schedule": {
                "times": ["11:00", "17:00"],
                "day_filter": "weekends",
                "timezone": "Europe/Moscow"
            }
        },
        {
            "name": "Every day",
            "schedule": {
                "times": ["08:00", "14:00", "20:00"],
                "day_filter": "all",
                "timezone": "Europe/Moscow"
            }
        },
        {
            "name": "Frequent weekday reminders",
            "schedule": {
                "times": ["09:00", "11:00", "13:00", "15:00", "17:00", "19:00", "21:00"],
                "day_filter": "weekdays",
                "timezone": "Europe/Moscow"
            }
        }
    ]

    for test_case in test_schedules:
        print(f"   Testing: {test_case['name']}")
        db.set_reminder_schedule(test_user_id, test_case['schedule'])
        await scheduler.schedule_user_reminders(test_user_id)

        jobs = scheduler.get_user_jobs(test_user_id)
        print(f"   ✓ Scheduled {len(jobs)} jobs")

        if jobs:
            print(f"   Next reminder: {jobs[0].next_run_time}")
        print()

    # 6. Test removing reminders
    print("6. Testing reminder removal...")
    scheduler.remove_user_reminders(test_user_id)
    jobs = scheduler.get_user_jobs(test_user_id)
    print(f"   ✓ Jobs after removal: {len(jobs)}")
    print()

    # 7. Test multi-user scheduling
    print("7. Testing multi-user scheduling...")
    test_user_2 = 987654321
    db.ensure_user_exists(test_user_2)

    schedule_user_1 = {
        "times": ["10:00", "15:00"],
        "day_filter": "weekdays",
        "timezone": "Europe/Moscow"
    }

    schedule_user_2 = {
        "times": ["12:00", "18:00"],
        "day_filter": "all",
        "timezone": "Europe/Moscow"
    }

    db.set_reminder_schedule(test_user_id, schedule_user_1)
    db.set_reminder_schedule(test_user_2, schedule_user_2)

    await scheduler.schedule_user_reminders(test_user_id)
    await scheduler.schedule_user_reminders(test_user_2)

    jobs_user_1 = scheduler.get_user_jobs(test_user_id)
    jobs_user_2 = scheduler.get_user_jobs(test_user_2)

    print(f"   ✓ User 1 jobs: {len(jobs_user_1)}")
    print(f"   ✓ User 2 jobs: {len(jobs_user_2)}")
    print()

    # 8. Cleanup
    print("8. Cleaning up test data...")
    scheduler.remove_user_reminders(test_user_id)
    scheduler.remove_user_reminders(test_user_2)
    db.clear_all_user_data(test_user_id)
    db.clear_all_user_data(test_user_2)
    print("   ✓ Cleanup complete\n")

    # Note about persistence
    print("=" * 80)
    print("NOTE: Jobs are persisted to SQLite job store")
    print("They will survive bot restarts automatically")
    print("=" * 80)
    print()

    # Shutdown
    print("9. Shutting down scheduler...")
    scheduler.shutdown_scheduler()
    print("   ✓ Scheduler shut down gracefully\n")

    print("="*80)
    print("All scheduler tests completed! ✓")
    print("="*80)


async def test_immediate_reminder():
    """
    Test sending a reminder immediately (for debugging).

    This bypasses the scheduler and calls send_reminder directly.
    """
    print("\n" + "="*80)
    print("TESTING IMMEDIATE REMINDER")
    print("="*80 + "\n")

    test_user_id = 123456789
    mock_bot = MockBot()

    print("Sending immediate test reminder...")
    await scheduler.send_reminder(test_user_id, mock_bot)
    print("\n✓ Test reminder sent\n")


if __name__ == '__main__':
    import sys

    if len(sys.argv) > 1 and sys.argv[1] == '--immediate':
        print("Running immediate reminder test...")
        asyncio.run(test_immediate_reminder())
    else:
        print("Running full scheduler test suite...")
        asyncio.run(test_scheduler())
