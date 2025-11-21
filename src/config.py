"""
Configuration module for Kick bot.
Loads environment variables and defines constants.

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

import os
import logging
from pathlib import Path
from dotenv import load_dotenv

# Setup logging
logger = logging.getLogger(__name__)

# Load environment variables from .env file
env_path = Path(__file__).parent.parent / '.env'
load_dotenv(env_path)

# Telegram Bot Token
TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')

# OpenAI API Key
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')

# Bot Password (shared by all users)
BOT_PASSWORD = os.getenv('BOT_PASSWORD')

# Validate required environment variables
if not TELEGRAM_BOT_TOKEN:
    raise ValueError("TELEGRAM_BOT_TOKEN not found in .env file")
if not OPENAI_API_KEY:
    raise ValueError("OPENAI_API_KEY not found in .env file")
if not BOT_PASSWORD:
    raise ValueError("BOT_PASSWORD not found in .env file")

# Telegram message limits
MAX_MESSAGE_LENGTH = 4096

# Database configuration
DATABASE_PATH = Path(__file__).parent / 'data' / 'kick.db'

# Bot communication phrases (strictly neutral, no emojis)
class BotPhrases:
    """All allowed bot phrases - strictly neutral communication only."""

    # Authentication
    AUTH_REQUEST = "Введите пароль для доступа."
    AUTH_SUCCESS = "Доступ разрешен."
    AUTH_FAILED = "Неверный пароль. Попробуйте еще раз."

    # Reminder prompts
    REMINDER_PROMPT = "Готов записать наблюдение?"
    REMINDER_CONFIGURED = "Напоминания настроены."
    REMINDER_REQUEST = "Отправь расписание напоминаний в свободной форме."

    # Practice mode
    PRACTICE_START = "Отправь голосовое сообщение или напиши текст."
    PRACTICE_NEXT_STEP = "Перейти к следующему шагу?"
    PRACTICE_COMPLETE_PROMPT = "Завершить запись?"
    PRACTICE_SAVED = "Запись сохранена."

    # Practice fields
    FIELD_CONTENT = "Обрати внимание на какое-то содержание, которое находится в поле внимания (внутреннее или внешнее)."
    FIELD_ATTITUDE = "Осознай своё отношение к этому содержанию - обрати внимание на тело, на баланс расслабления и напряжения по поводу этого содержания."
    FIELD_FORM = "Подбери свою форму выражения этого отношения, вербализовав его, используя наши формы согласия и отрицания (да-принимающее, нет-принимающее, да-отрицающее, нет-отрицающее)."
    FIELD_BODY = "Озвучь для себя и обрати внимание соответствует ли то, что ты осознал телесной реакции."
    FIELD_RESPONSE = "Обрати внимание, что будет происходить с тобой после осознания."

    # Diary mode
    DIARY_PROMPT = "Отправь голосовое сообщение или напиши текст."
    DIARY_SAVED = "Запись сохранена."

    # Input refinement
    INPUT_CONFIRM = "Всё ок"
    INPUT_QUESTIONS = "Задать наводящие вопросы по теме"
    INPUT_COMPLETE = "Завершить"

    # Transcription
    TRANSCRIPTION_READY = "Транскрипция готова. Проверьте текст."

    # Export
    EXPORT_PROMPT = "Выберите формат экспорта."
    EXPORT_READY = "Вот записи за выбранный период."

    # Data management
    DATA_CLEARED = "Все записи удалены."
    DATA_CLEAR_CONFIRM = "Вы уверены? Все записи будут удалены без возможности восстановления."

    # Buttons
    BTN_YES_GUIDED = "Да"
    BTN_NO = "Нет"
    BTN_OK = "Всё ок"
    BTN_REWRITE = "Переписать ответ"
    BTN_QUESTIONS = "Задать наводящие вопросы"
    BTN_COMPLETE = "Завершить"
    BTN_NEXT = "Далее"
    BTN_EXPORT_JSON = "JSON"
    BTN_EXPORT_TXT = "TXT"
    BTN_CONFIRM_DELETE = "Да, удалить всё"
    BTN_CANCEL = "Отмена"

# Practice fields configuration
PRACTICE_FIELDS = [
    {
        'name': 'content',
        'prompt': BotPhrases.FIELD_CONTENT,
        'required': True
    },
    {
        'name': 'attitude',
        'prompt': BotPhrases.FIELD_ATTITUDE,
        'required': True
    },
    {
        'name': 'form',
        'prompt': BotPhrases.FIELD_FORM,
        'required': True
    },
    {
        'name': 'body',
        'prompt': BotPhrases.FIELD_BODY,
        'required': True
    },
    {
        'name': 'response',
        'prompt': BotPhrases.FIELD_RESPONSE,
        'required': True
    }
]

# OpenAI models
OPENAI_MODEL_GPT5 = "gpt5--mini"
OPENAI_MODEL_WHISPER = "whisper-1"

# GPT System Prompts
class SystemPrompts:
    """System prompts for GPT tasks."""

    SCHEDULE_PARSER = """Speak Russian. Parse natural language reminder request into specific times.

You will receive current date/time context at the beginning of the user's message. Use this context to interpret:
- Relative time references like "завтра" (tomorrow), "сегодня" (today), "через час" (in an hour)
- Weekday references like "в будни" (weekdays), "в понедельник" (on Monday)
- Time-relative phrases like "после обеда" (after lunch), based on current time

If request is vague, make reasonable assumptions:
- Morning (утро): 08:00-12:00
- Lunch (обед): 12:00-14:00
- Afternoon (день): 14:00-18:00
- Evening (вечер): 18:00-22:00
- "Often" or "frequently" (часто): every 2-3 hours

Output ONLY a valid JSON object in this exact format:
{
  "times": ["HH:MM", "HH:MM", ...],
  "day_filter": "all" | "weekdays" | "weekends",
  "timezone": "<user's timezone from context>"
}

day_filter values:
- "all": every day (Monday-Sunday)
- "weekdays": Monday to Friday only
- "weekends": Saturday and Sunday only

IMPORTANT: Use the timezone provided in the context for the "timezone" field.

Do NOT add any explanations, markdown, or extra text. Just the JSON object."""

    GUIDING_QUESTIONS = """
    """

logger.info("Configuration loaded successfully")
logger.info(f"Database path: {DATABASE_PATH}")
