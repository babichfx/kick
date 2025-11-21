"""
Message accumulator utility for handling multi-part text messages.
Buffers messages for 0.5 seconds to collect all parts before processing.
"""

import logging
import asyncio
from typing import Dict, Callable, Awaitable, Any

logger = logging.getLogger(__name__)

# Storage for accumulated message parts per user
_message_parts: Dict[int, list[str]] = {}

# Storage for active timer tasks per user
_timers: Dict[int, asyncio.Task] = {}


async def accumulate_message(
    user_id: int,
    text: str,
    callback: Callable[[int, str], Awaitable[Any]],
    delay: float = 0.5
) -> None:
    """
    Accumulate message parts with debouncing.

    When a user sends multiple messages in quick succession, this function
    buffers them for `delay` seconds before calling the callback with the
    combined text.

    Args:
        user_id: Telegram user ID
        text: Message text to accumulate
        callback: Async function to call with (user_id, combined_text)
        delay: Debounce delay in seconds (default: 0.5)
    """
    # Initialize message parts list if first message
    if user_id not in _message_parts:
        _message_parts[user_id] = []

    # Add message part
    _message_parts[user_id].append(text)
    logger.debug(f"Accumulated message part for user {user_id}, total parts: {len(_message_parts[user_id])}")

    # Cancel existing timer if any
    if user_id in _timers:
        _timers[user_id].cancel()
        logger.debug(f"Cancelled previous timer for user {user_id}")

    # Start new timer with proper task creation
    async def _timer_wrapper():
        await asyncio.sleep(delay)
        await _process_accumulated_messages(user_id, callback)

    task = asyncio.create_task(_timer_wrapper())
    _timers[user_id] = task
    logger.debug(f"Started new timer for user {user_id} with {delay}s delay")


async def _process_accumulated_messages(
    user_id: int,
    callback: Callable[[int, str], Awaitable[Any]]
) -> None:
    """
    Process accumulated messages by calling the callback.

    Internal function called by timer after debounce delay.

    Args:
        user_id: Telegram user ID
        callback: Async function to call with accumulated text
    """
    try:
        if user_id not in _message_parts:
            logger.warning(f"No message parts found for user {user_id}")
            return

        # Combine accumulated message parts
        full_text = ' '.join(_message_parts[user_id])
        logger.info(f"Processing accumulated message for user {user_id}, length: {len(full_text)}")

        # Call the callback with combined text
        await callback(user_id, full_text)

        # Clean up
        del _message_parts[user_id]
        if user_id in _timers:
            del _timers[user_id]
        logger.debug(f"Cleared accumulator for user {user_id}")

    except Exception as e:
        logger.error(f"Error processing accumulated messages for user {user_id}: {e}")
        # Clean up on error
        if user_id in _message_parts:
            del _message_parts[user_id]
        if user_id in _timers:
            del _timers[user_id]


def clear_accumulator(user_id: int) -> None:
    """
    Clear accumulated messages for a user.

    Use this to cancel message accumulation if the user exits a flow.

    Args:
        user_id: Telegram user ID
    """
    # Cancel timer if exists
    if user_id in _timers:
        _timers[user_id].cancel()
        del _timers[user_id]
        logger.debug(f"Cancelled timer for user {user_id}")

    # Clear message parts
    if user_id in _message_parts:
        del _message_parts[user_id]
        logger.debug(f"Cleared message parts for user {user_id}")


def get_accumulated_text(user_id: int) -> str:
    """
    Get currently accumulated text for a user without processing.

    Useful for debugging or previewing accumulated text.

    Args:
        user_id: Telegram user ID

    Returns:
        Combined accumulated text, or empty string if none
    """
    if user_id not in _message_parts:
        return ""
    return ' '.join(_message_parts[user_id])


def has_pending_messages(user_id: int) -> bool:
    """
    Check if user has pending accumulated messages.

    Args:
        user_id: Telegram user ID

    Returns:
        True if user has accumulated messages waiting to be processed
    """
    return user_id in _message_parts and len(_message_parts[user_id]) > 0
