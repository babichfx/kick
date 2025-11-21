"""
Database module for Kick bot.
Implements SQLite database with per-user data isolation.

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

import sqlite3
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Optional, List, Dict, Any
from contextlib import contextmanager

from config import DATABASE_PATH

logger = logging.getLogger(__name__)


@contextmanager
def get_db_connection():
    """Context manager for database connections with WAL mode."""
    conn = sqlite3.connect(DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute('PRAGMA journal_mode=WAL')
    try:
        yield conn
        conn.commit()
    except Exception as e:
        conn.rollback()
        logger.error(f"Database error: {e}")
        raise
    finally:
        conn.close()


def init_database():
    """Initialize database with schema."""
    DATABASE_PATH.parent.mkdir(parents=True, exist_ok=True)

    with get_db_connection() as conn:
        cursor = conn.cursor()

        # Users table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                telegram_user_id INTEGER PRIMARY KEY,
                is_authenticated INTEGER NOT NULL DEFAULT 0,
                first_auth_date TEXT,
                last_active TEXT,
                reminder_schedule TEXT,
                timezone TEXT DEFAULT 'Europe/Moscow'
            )
        ''')

        # Entries table (structured practice only - all fields required)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS entries (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                telegram_user_id INTEGER NOT NULL,
                date TEXT NOT NULL,
                content TEXT NOT NULL,
                attitude TEXT NOT NULL,
                form TEXT NOT NULL,
                body TEXT NOT NULL,
                response TEXT NOT NULL,
                FOREIGN KEY (telegram_user_id) REFERENCES users(telegram_user_id)
            )
        ''')

        # Refusals table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS refusals (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                telegram_user_id INTEGER NOT NULL,
                date TEXT NOT NULL,
                FOREIGN KEY (telegram_user_id) REFERENCES users(telegram_user_id)
            )
        ''')

        # Create indexes for performance
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_entries_user_date
            ON entries(telegram_user_id, date)
        ''')

        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_refusals_user_date
            ON refusals(telegram_user_id, date)
        ''')

        logger.info("Database initialized successfully")


# ============================================
# User Operations
# ============================================

def get_user(telegram_user_id: int) -> Optional[Dict[str, Any]]:
    """Get user by telegram_user_id."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            'SELECT * FROM users WHERE telegram_user_id = ?',
            (telegram_user_id,)
        )
        row = cursor.fetchone()
        return dict(row) if row else None


def create_user(telegram_user_id: int) -> None:
    """Create new user."""
    now = datetime.now().isoformat()
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO users (telegram_user_id, first_auth_date, last_active)
            VALUES (?, ?, ?)
        ''', (telegram_user_id, now, now))
        logger.info(f"Created user: {telegram_user_id}")


def update_user_auth(telegram_user_id: int, is_authenticated: bool) -> None:
    """Update user authentication status."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            UPDATE users
            SET is_authenticated = ?, last_active = ?
            WHERE telegram_user_id = ?
        ''', (1 if is_authenticated else 0, datetime.now().isoformat(), telegram_user_id))
        logger.info(f"Updated auth for user {telegram_user_id}: {is_authenticated}")


def update_user_activity(telegram_user_id: int) -> None:
    """Update last active timestamp."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            UPDATE users
            SET last_active = ?
            WHERE telegram_user_id = ?
        ''', (datetime.now().isoformat(), telegram_user_id))


def set_reminder_schedule(telegram_user_id: int, schedule: Dict[str, Any]) -> None:
    """Save user's reminder schedule (parsed by GPT)."""
    # Ensure user exists before updating
    ensure_user_exists(telegram_user_id)

    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            UPDATE users
            SET reminder_schedule = ?
            WHERE telegram_user_id = ?
        ''', (json.dumps(schedule) if schedule else None, telegram_user_id))

        # Verify the update was successful
        if cursor.rowcount == 0:
            logger.error(f"Failed to save reminder schedule for user {telegram_user_id} - no rows updated")
            raise ValueError(f"User {telegram_user_id} not found in database")

        logger.info(f"Saved reminder schedule for user {telegram_user_id}")


def get_reminder_schedule(telegram_user_id: int) -> Optional[Dict[str, Any]]:
    """Get user's reminder schedule."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            'SELECT reminder_schedule FROM users WHERE telegram_user_id = ?',
            (telegram_user_id,)
        )
        row = cursor.fetchone()

        if not row:
            logger.warning(f"User {telegram_user_id} not found when getting reminder schedule")
            return None

        if row['reminder_schedule']:
            schedule = json.loads(row['reminder_schedule'])
            logger.debug(f"Retrieved reminder schedule for user {telegram_user_id}: {schedule}")
            return schedule

        logger.debug(f"No reminder schedule set for user {telegram_user_id}")
        return None


def get_user_timezone(telegram_user_id: int) -> str:
    """Get user's timezone. Returns 'Europe/Moscow' as default."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            'SELECT timezone FROM users WHERE telegram_user_id = ?',
            (telegram_user_id,)
        )
        row = cursor.fetchone()

        if not row:
            logger.warning(f"User {telegram_user_id} not found when getting timezone")
            return 'Europe/Moscow'

        timezone = row['timezone'] or 'Europe/Moscow'
        logger.debug(f"Retrieved timezone for user {telegram_user_id}: {timezone}")
        return timezone


def set_user_timezone(telegram_user_id: int, timezone: str) -> None:
    """Set user's timezone."""
    # Ensure user exists before updating
    ensure_user_exists(telegram_user_id)

    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            UPDATE users
            SET timezone = ?
            WHERE telegram_user_id = ?
        ''', (timezone, telegram_user_id))

        # Verify the update was successful
        if cursor.rowcount == 0:
            logger.error(f"Failed to set timezone for user {telegram_user_id} - no rows updated")
            raise ValueError(f"User {telegram_user_id} not found in database")

        logger.info(f"Set timezone for user {telegram_user_id}: {timezone}")


# ============================================
# Entry Operations
# ============================================

def create_entry(
    telegram_user_id: int,
    content: str,
    attitude: str,
    form: str,
    body: str,
    response: str
) -> int:
    """Create new structured practice entry (all fields required)."""
    now = datetime.now().isoformat()
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO entries
            (telegram_user_id, date, content, attitude, form, body, response)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (telegram_user_id, now, content, attitude, form, body, response))
        entry_id = cursor.lastrowid
        logger.info(f"Created entry {entry_id} for user {telegram_user_id}")
        return entry_id


def get_user_entries(
    telegram_user_id: int,
    limit: Optional[int] = None,
    offset: int = 0
) -> List[Dict[str, Any]]:
    """Get all entries for a user."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        query = '''
            SELECT * FROM entries
            WHERE telegram_user_id = ?
            ORDER BY date DESC
        '''
        if limit:
            query += f' LIMIT {limit} OFFSET {offset}'

        cursor.execute(query, (telegram_user_id,))
        rows = cursor.fetchall()
        return [dict(row) for row in rows]


def get_entry_count(telegram_user_id: int) -> int:
    """Get total entry count for a user."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            'SELECT COUNT(*) as count FROM entries WHERE telegram_user_id = ?',
            (telegram_user_id,)
        )
        return cursor.fetchone()['count']


def delete_user_entries(telegram_user_id: int) -> None:
    """Delete all entries for a user."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            'DELETE FROM entries WHERE telegram_user_id = ?',
            (telegram_user_id,)
        )
        logger.info(f"Deleted all entries for user {telegram_user_id}")


# ============================================
# Refusal Operations
# ============================================

def create_refusal(telegram_user_id: int) -> int:
    """Record when user declines a reminder."""
    now = datetime.now().isoformat()
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO refusals (telegram_user_id, date)
            VALUES (?, ?)
        ''', (telegram_user_id, now))
        refusal_id = cursor.lastrowid
        logger.info(f"Recorded refusal {refusal_id} for user {telegram_user_id}")
        return refusal_id


def get_user_refusals(
    telegram_user_id: int,
    limit: Optional[int] = None
) -> List[Dict[str, Any]]:
    """Get refusal history for a user."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        query = '''
            SELECT * FROM refusals
            WHERE telegram_user_id = ?
            ORDER BY date DESC
        '''
        if limit:
            query += f' LIMIT {limit}'

        cursor.execute(query, (telegram_user_id,))
        rows = cursor.fetchall()
        return [dict(row) for row in rows]


def delete_user_refusals(telegram_user_id: int) -> None:
    """Delete all refusals for a user."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            'DELETE FROM refusals WHERE telegram_user_id = ?',
            (telegram_user_id,)
        )
        logger.info(f"Deleted all refusals for user {telegram_user_id}")


# ============================================
# Utility Functions
# ============================================

def is_user_authenticated(telegram_user_id: int) -> bool:
    """Check if user is authenticated."""
    user = get_user(telegram_user_id)
    return user is not None and user['is_authenticated'] == 1


def ensure_user_exists(telegram_user_id: int) -> None:
    """Create user if doesn't exist."""
    if not get_user(telegram_user_id):
        create_user(telegram_user_id)


def clear_all_user_data(telegram_user_id: int) -> None:
    """Completely remove all user data."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('DELETE FROM entries WHERE telegram_user_id = ?', (telegram_user_id,))
        cursor.execute('DELETE FROM refusals WHERE telegram_user_id = ?', (telegram_user_id,))
        cursor.execute('DELETE FROM users WHERE telegram_user_id = ?', (telegram_user_id,))
        logger.info(f"Cleared all data for user {telegram_user_id}")


# ============================================
# Main (for testing/initialization)
# ============================================

if __name__ == '__main__':
    import sys

    if len(sys.argv) > 1 and sys.argv[1] == '--init':
        print("Initializing database...")
        init_database()
        print(f"Database initialized at: {DATABASE_PATH}")
    else:
        print("Usage: python database.py --init")
