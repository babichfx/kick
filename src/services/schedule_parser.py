"""
Schedule Parser Service.
Uses GPT to parse natural language reminder requests into structured time schedules.

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

import json
import logging
import re
from datetime import datetime
from typing import Dict, List, Optional
from openai import AsyncOpenAI
import pytz

from config import OPENAI_API_KEY, SystemPrompts

logger = logging.getLogger(__name__)

# Initialize OpenAI client
client = AsyncOpenAI(api_key=OPENAI_API_KEY)


async def parse_schedule(user_input: str, user_timezone: str = "Europe/Moscow") -> Optional[Dict[str, any]]:
    """
    Parse natural language reminder request into structured schedule.

    Uses GPT to interpret vague time references and make reasonable assumptions.
    GPT NEVER asks for clarification - it always makes a decision.

    Examples:
        "Напоминай мне с 9 до 22 каждые 2 часа"
        -> {"times": ["09:00", "11:00", "13:00", "15:00", "17:00", "19:00", "21:00"], "day_filter": "all", "timezone": "Europe/Moscow"}

        "Ping me 5 times from 13:00 to 14:00"
        -> {"times": ["13:00", "13:15", "13:30", "13:45", "14:00"], "day_filter": "all", "timezone": "Europe/Moscow"}

        "В будни в 10:00, 13:00, 17:00 и 21:00"
        -> {"times": ["10:00", "13:00", "17:00", "21:00"], "day_filter": "weekdays", "timezone": "Europe/Moscow"}

        "По выходным в 11:00 и 17:00"
        -> {"times": ["11:00", "17:00"], "day_filter": "weekends", "timezone": "Europe/Moscow"}

        "Напоминай с утра до обеда" (vague - GPT decides)
        -> {"times": ["09:00", "11:00", "13:00"], "day_filter": "all", "timezone": "Europe/Moscow"}

    Args:
        user_input: Natural language reminder request in Russian or English
        user_timezone: User's timezone (e.g., "Europe/Moscow")

    Returns:
        Dict with structure:
        {
            "times": ["HH:MM", "HH:MM", ...],  # List of specific times
            "day_filter": str,                  # "all", "weekdays", or "weekends"
            "timezone": str                     # Timezone string (e.g., "Europe/Moscow")
        }
        Returns None if parsing fails
    """
    try:
        logger.info(f"Parsing schedule request: {user_input[:100]} (timezone: {user_timezone})")

        # Get current datetime in user's timezone
        tz = pytz.timezone(user_timezone)
        now = datetime.now(tz)

        # Format context with current date, time, and day of week
        day_names_en = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
        day_names_ru = ['Понедельник', 'Вторник', 'Среда', 'Четверг', 'Пятница', 'Суббота', 'Воскресенье']
        day_name_en = day_names_en[now.weekday()]
        day_name_ru = day_names_ru[now.weekday()]

        context = (
            f"Context: Today is {day_name_en} ({day_name_ru}), "
            f"{now.strftime('%Y-%m-%d')}, current time is {now.strftime('%H:%M')} "
            f"(timezone: {user_timezone}).\n\n"
            f"User request: {user_input}"
        )

        logger.debug(f"Injecting context: {context[:200]}")

        # Call GPT with schedule parsing system prompt
        response = await client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": SystemPrompts.SCHEDULE_PARSER},
                {"role": "user", "content": context}
            ],
            temperature=0.3,  # Low temperature for more consistent parsing
            max_tokens=500
        )

        response_text = response.choices[0].message.content.strip()
        logger.debug(f"GPT response: {response_text}")

        # Parse JSON response
        schedule = _parse_json_response(response_text)

        if not schedule:
            logger.error("Failed to parse JSON from GPT response")
            return None

        # Validate schedule structure
        if not _validate_schedule(schedule):
            logger.error(f"Invalid schedule structure: {schedule}")
            return None

        logger.info(f"Successfully parsed schedule with {len(schedule['times'])} times")
        return schedule

    except Exception as e:
        logger.error(f"Error parsing schedule: {e}")
        return None


def _parse_json_response(response_text: str) -> Optional[Dict]:
    """
    Extract and parse JSON from GPT response.

    GPT might wrap JSON in markdown code blocks or add extra text.
    This function extracts the JSON and parses it.

    Args:
        response_text: Raw GPT response text

    Returns:
        Parsed JSON dict, or None if parsing fails
    """
    try:
        # Try direct JSON parse first
        return json.loads(response_text)
    except json.JSONDecodeError:
        # GPT might have wrapped in markdown code block
        # Extract JSON from ```json ... ``` or ``` ... ```
        json_pattern = r'```(?:json)?\s*(\{.*?\})\s*```'
        match = re.search(json_pattern, response_text, re.DOTALL)

        if match:
            try:
                return json.loads(match.group(1))
            except json.JSONDecodeError:
                pass

        # Try to find any JSON object in the text
        json_pattern = r'\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}'
        match = re.search(json_pattern, response_text, re.DOTALL)

        if match:
            try:
                return json.loads(match.group(0))
            except json.JSONDecodeError:
                pass

        logger.error(f"Could not extract valid JSON from response: {response_text[:200]}")
        return None


def _validate_schedule(schedule: Dict) -> bool:
    """
    Validate schedule structure and data.

    Required fields:
    - times: non-empty list of strings in HH:MM format
    - day_filter: "all", "weekdays", or "weekends"
    - timezone: non-empty string

    Args:
        schedule: Parsed schedule dict

    Returns:
        True if valid, False otherwise
    """
    # Check required fields exist
    if not isinstance(schedule, dict):
        return False

    if 'times' not in schedule or 'day_filter' not in schedule or 'timezone' not in schedule:
        logger.error("Missing required fields in schedule")
        return False

    # Validate times
    times = schedule['times']
    if not isinstance(times, list) or len(times) == 0:
        logger.error("times must be non-empty list")
        return False

    # Validate time format (HH:MM)
    time_pattern = re.compile(r'^([0-1][0-9]|2[0-3]):[0-5][0-9]$')
    for time_str in times:
        if not isinstance(time_str, str) or not time_pattern.match(time_str):
            logger.error(f"Invalid time format: {time_str}")
            return False

    # Validate day_filter
    day_filter = schedule['day_filter']
    if not isinstance(day_filter, str) or day_filter not in ['all', 'weekdays', 'weekends']:
        logger.error(f"day_filter must be 'all', 'weekdays', or 'weekends', got: {day_filter}")
        return False

    # Validate timezone
    if not isinstance(schedule['timezone'], str) or len(schedule['timezone']) == 0:
        logger.error("timezone must be non-empty string")
        return False

    return True


def format_schedule_summary(schedule: Dict) -> str:
    """
    Format schedule as human-readable summary for confirmation.

    Args:
        schedule: Validated schedule dict

    Returns:
        Human-readable summary string
    """
    times = schedule['times']
    day_filter = schedule['day_filter']
    timezone = schedule['timezone']

    times_str = ", ".join(times)

    # Format day filter
    day_filter_map = {
        'all': '',
        'weekdays': ' (только в будни)',
        'weekends': ' (только в выходные)'
    }
    day_filter_str = day_filter_map.get(day_filter, '')

    return f"Напоминания в {times_str}{day_filter_str} ({timezone})"
