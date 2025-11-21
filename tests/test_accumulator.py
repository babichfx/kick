"""
Test script for message accumulator utility.
"""

import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

import asyncio
import logging
from src.services.message_accumulator import (
    accumulate_message,
    clear_accumulator,
    get_accumulated_text,
    has_pending_messages
)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# Mock callback function
accumulated_results = {}


async def mock_callback(user_id: int, text: str) -> None:
    """Mock callback to capture accumulated text."""
    accumulated_results[user_id] = text
    logger.info(f"Callback received: user_id={user_id}, text='{text}'")


async def test_single_message():
    """Test accumulating a single message."""
    logger.info("\n=== Test 1: Single message ===")
    user_id = 1

    await accumulate_message(user_id, "Hello", mock_callback)

    # Wait for timer to fire
    await asyncio.sleep(0.6)

    assert user_id in accumulated_results, "Callback should have been called"
    assert accumulated_results[user_id] == "Hello", "Text should match"
    assert not has_pending_messages(user_id), "No pending messages should remain"

    logger.info("✓ Test 1 passed")


async def test_multiple_messages():
    """Test accumulating multiple messages."""
    logger.info("\n=== Test 2: Multiple messages ===")
    user_id = 2
    accumulated_results.clear()

    await accumulate_message(user_id, "Hello", mock_callback)
    await asyncio.sleep(0.2)  # Wait less than debounce delay

    await accumulate_message(user_id, "World", mock_callback)
    await asyncio.sleep(0.2)

    await accumulate_message(user_id, "Test", mock_callback)

    # Wait for timer to fire
    await asyncio.sleep(0.6)

    assert user_id in accumulated_results, "Callback should have been called"
    assert accumulated_results[user_id] == "Hello World Test", "Text should be combined"
    assert not has_pending_messages(user_id), "No pending messages should remain"

    logger.info("✓ Test 2 passed")


async def test_clear_accumulator():
    """Test clearing accumulator before processing."""
    logger.info("\n=== Test 3: Clear accumulator ===")
    user_id = 3
    accumulated_results.clear()

    await accumulate_message(user_id, "Test message", mock_callback)

    # Clear before timer fires
    assert has_pending_messages(user_id), "Should have pending messages"
    clear_accumulator(user_id)
    assert not has_pending_messages(user_id), "Pending messages should be cleared"

    # Wait to ensure callback is not called
    await asyncio.sleep(0.6)

    assert user_id not in accumulated_results, "Callback should not have been called"

    logger.info("✓ Test 3 passed")


async def test_get_accumulated_text():
    """Test getting accumulated text without processing."""
    logger.info("\n=== Test 4: Get accumulated text ===")
    user_id = 4
    accumulated_results.clear()

    await accumulate_message(user_id, "Part 1", mock_callback)
    await asyncio.sleep(0.2)

    await accumulate_message(user_id, "Part 2", mock_callback)

    # Get text before processing
    text = get_accumulated_text(user_id)
    assert text == "Part 1 Part 2", "Should return accumulated text"

    # Wait for processing
    await asyncio.sleep(0.6)

    # After processing, should be empty
    text = get_accumulated_text(user_id)
    assert text == "", "Should be empty after processing"

    logger.info("✓ Test 4 passed")


async def test_multiple_users():
    """Test accumulator with multiple users simultaneously."""
    logger.info("\n=== Test 5: Multiple users ===")
    accumulated_results.clear()

    # User 5
    await accumulate_message(5, "User 5 message", mock_callback)

    # User 6
    await accumulate_message(6, "User 6 part 1", mock_callback)
    await asyncio.sleep(0.2)
    await accumulate_message(6, "User 6 part 2", mock_callback)

    # Wait for both to process
    await asyncio.sleep(0.6)

    assert 5 in accumulated_results, "User 5 callback should be called"
    assert 6 in accumulated_results, "User 6 callback should be called"
    assert accumulated_results[5] == "User 5 message", "User 5 text should match"
    assert accumulated_results[6] == "User 6 part 1 User 6 part 2", "User 6 text should be combined"

    logger.info("✓ Test 5 passed")


async def main():
    """Run all tests."""
    logger.info("Starting message accumulator tests...")

    try:
        await test_single_message()
        await test_multiple_messages()
        await test_clear_accumulator()
        await test_get_accumulated_text()
        await test_multiple_users()

        logger.info("\n✅ All tests passed!")
    except AssertionError as e:
        logger.error(f"\n❌ Test failed: {e}")
    except Exception as e:
        logger.error(f"\n❌ Error during tests: {e}")


if __name__ == "__main__":
    asyncio.run(main())
