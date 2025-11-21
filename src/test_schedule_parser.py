"""
Test schedule parser service.
Tests natural language parsing with various inputs including vague requests.

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
from services.schedule_parser import parse_schedule, format_schedule_summary

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def test_schedule_parser():
    """Test schedule parser with various inputs."""

    test_cases = [
        # Specific times
        "Напоминай мне с 9 до 22 каждые 2 часа",
        "Ping me 5 times from 13:00 to 14:00",
        "В будни в 10:00, 13:00, 17:00 и 21:00",

        # Weekends only
        "По выходным в 11:00 и 17:00",
        "Только в субботу и воскресенье утром",
        "Weekend reminders at 10am and 8pm",

        # Vague times (GPT must decide)
        "Напоминай с утра до обеда",
        "Несколько раз днем",
        "Часто напоминай с утра до вечера",
        "Утром, днем и вечером",

        # Mixed
        "Напоминай каждые 3 часа с 8 утра до 8 вечера в будни",
        "Ping me every hour during work hours on weekdays",

        # Edge cases
        "Напоминай один раз в полдень",
        "В 9:00 и 21:00 каждый день",
    ]

    print("\n" + "="*80)
    print("TESTING SCHEDULE PARSER")
    print("="*80 + "\n")

    for i, test_input in enumerate(test_cases, 1):
        print(f"\n--- Test Case {i} ---")
        print(f"Input: {test_input}")
        print()

        schedule = await parse_schedule(test_input)

        if schedule:
            print("✓ Parsing successful!")
            print(f"  Times: {schedule['times']}")
            print(f"  Day filter: {schedule['day_filter']}")
            print(f"  Timezone: {schedule['timezone']}")
            print(f"\n  Summary: {format_schedule_summary(schedule)}")
        else:
            print("✗ Parsing failed!")

        print()

    print("="*80)
    print("TESTING COMPLETE")
    print("="*80 + "\n")


if __name__ == "__main__":
    asyncio.run(test_schedule_parser())
