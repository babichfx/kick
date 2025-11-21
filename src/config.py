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
    FIELD_CONTENT = "Содержание: что в поле внимания?"
    FIELD_ATTITUDE = "Отношение: баланс напряжения и расслабления в теле?"
    FIELD_FORM = "Форма согласия: да-принимающее, нет-принимающее, да-отвергающее, нет-отвергающее?"
    FIELD_BODY = "Реакция тела: осознавание совпадает с реакцией тела?"
    FIELD_RESPONSE = "Изменения: что происходит после осознавания?"

    # Diary mode
    DIARY_PROMPT = "Отправь голосовое сообщение или напиши текст."
    DIARY_SAVED = "Запись сохранена."

    # Input refinement
    INPUT_CONFIRM = "Всё ок"
    INPUT_REFINE = "Уточнить/добавить"
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
    BTN_YES_GUIDED = "Да, пошагово"
    BTN_YES_FREE = "Да"
    BTN_NO = "Нет"
    BTN_OK = "Всё ок"
    BTN_REFINE = "Уточнить/добавить"
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
If request is vague (e.g., "morning", "lunch time", "often"), make reasonable assumptions:
- Morning (утро): 08:00-12:00
- Lunch (обед): 12:00-14:00
- Afternoon (день): 14:00-18:00
- Evening (вечер): 18:00-22:00
- "Often" or "frequently" (часто): every 2-3 hours

Output ONLY a valid JSON object in this exact format:
{
  "times": ["HH:MM", "HH:MM", ...],
  "weekdays_only": true/false,
  "timezone": "Europe/Moscow"
}

Do NOT add any explanations, markdown, or extra text. Just the JSON object."""

    ENTRY_SUMMARIZER = """Speak Russian. Extract structured fields from user's awareness practice text.
Use ONLY the user's exact words - do not interpret, add, or modify anything.

Output ONLY a valid JSON object in this exact format:
{
  "content": "exact user words about what's in field of attention",
  "attitude": "exact user words about body status and tension/relaxation",
  "form": "exact user words about acceptance/rejection form",
  "body": "exact user words about body reaction match",
  "response": "exact user words about what changed"
}

If a field is not mentioned, use empty string "".
Do NOT add any explanations, markdown, or extra text. Just the JSON object."""

    GUIDING_QUESTIONS = """

    """

logger.info("Configuration loaded successfully")
logger.info(f"Database path: {DATABASE_PATH}")
