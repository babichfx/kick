"""
Test and demonstration of Guided Practice handler.

This demonstrates the step-by-step practice flow with unlimited field refinement.

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

from src import database as db
from src.handlers.practice import (
    handle_practice_input,
    handle_practice_callback
)
from src.handlers.reminders import handle_reminder_response


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
            for row in reply_markup.inline_keyboard:
                for button in row:
                    print(f"  - {button.text}")
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


async def test_guided_practice_flow():
    """
    Test complete guided practice flow.

    Demonstrates:
    1. User starts practice from reminder
    2. User answers each field
    3. User can refine answers unlimited times
    4. Practice is saved to database
    """
    print("\n" + "="*80)
    print("TEST: GUIDED PRACTICE FLOW")
    print("="*80 + "\n")

    # Setup
    test_user_id = 111222333
    db.init_database()
    db.ensure_user_exists(test_user_id)
    db.update_user_auth(test_user_id, True)

    mock_bot = MockBot()
    context = MockContext(mock_bot)
    context.user_data['authenticated'] = True

    print("STEP 1: User responds to reminder with 'Да, пошагово'")
    update = MockUpdate("", test_user_id)
    update.callback_query = MockCallbackQuery('reminder_yes_guided', test_user_id)
    await handle_reminder_response(update, context)

    print(f"\n   State: mode={context.user_data.get('mode')}, field={context.user_data.get('current_field')}")

    # Field 1: Content
    print("\n" + "-"*80)
    print("STEP 2: User answers Field 1 (Содержание)")
    print("        User: 'Тревога по поводу встречи'")
    update = MockUpdate("Тревога по поводу встречи", test_user_id)
    await handle_practice_input(update, context)

    print(f"\n   Current answer: {context.user_data.get('current_answer')}")
    print("   [Bot shows answer with 'Всё ок' button and text 'Подтвердите ответ или добавьте что-то если необходимо']")

    # User adds more (no button click needed)
    print("\n   User sends more text: 'Страх не справиться'")
    update = MockUpdate("Страх не справиться", test_user_id)
    await handle_practice_input(update, context)

    print(f"\n   Accumulated answer: {context.user_data.get('current_answer')}")
    print("   [Bot shows accumulated answer with 'Всё ок' button]")

    # User confirms field 1
    print("\n   User clicks: 'Всё ок'")
    update = MockUpdate("", test_user_id)
    update.callback_query = MockCallbackQuery('field_ok', test_user_id)
    await handle_practice_callback(update, context)

    print(f"\n   Saved to practice_data: {context.user_data.get('practice_data')}")
    print(f"   Moved to field: {context.user_data.get('current_field')}")

    # Field 2: Attitude
    print("\n" + "-"*80)
    print("STEP 3: User answers Field 2 (Отношение)")
    print("        User: 'Напряжение в груди и плечах'")
    update = MockUpdate("Напряжение в груди и плечах", test_user_id)
    await handle_practice_input(update, context)

    # User confirms immediately
    print("\n   User clicks: 'Всё ок'")
    update = MockUpdate("", test_user_id)
    update.callback_query = MockCallbackQuery('field_ok', test_user_id)
    await handle_practice_callback(update, context)

    print(f"\n   Moved to field: {context.user_data.get('current_field')}")

    # Field 3: Form
    print("\n" + "-"*80)
    print("STEP 4: User answers Field 3 (Форма согласия)")
    print("        User: 'Нет-отвергающее'")
    update = MockUpdate("Нет-отвергающее", test_user_id)
    await handle_practice_input(update, context)

    print("\n   User clicks: 'Всё ок'")
    update = MockUpdate("", test_user_id)
    update.callback_query = MockCallbackQuery('field_ok', test_user_id)
    await handle_practice_callback(update, context)

    # Field 4: Body
    print("\n" + "-"*80)
    print("STEP 5: User answers Field 4 (Реакция тела)")
    print("        User: 'Да, совпадает'")
    update = MockUpdate("Да, совпадает", test_user_id)
    await handle_practice_input(update, context)

    print("\n   User clicks: 'Всё ок'")
    update = MockUpdate("", test_user_id)
    update.callback_query = MockCallbackQuery('field_ok', test_user_id)
    await handle_practice_callback(update, context)

    # Field 5: Response (last field)
    print("\n" + "-"*80)
    print("STEP 6: User answers Field 5 (Изменения) - LAST FIELD")
    print("        User: 'Напряжение немного уменьшилось'")
    update = MockUpdate("Напряжение немного уменьшилось", test_user_id)
    await handle_practice_input(update, context)

    print("\n   User clicks: 'Всё ок'")
    update = MockUpdate("", test_user_id)
    update.callback_query = MockCallbackQuery('field_ok', test_user_id)
    await handle_practice_callback(update, context)

    # Practice should be complete and saved
    print("\n" + "-"*80)
    print("STEP 7: Practice complete, saved to database")
    print(f"\n   Final mode: {context.user_data.get('mode')}")
    print(f"   Practice data cleared: {context.user_data.get('practice_data')}")

    # Verify entry was saved
    entries = db.get_user_entries(test_user_id)
    print(f"\n   Entries in database: {len(entries)}")
    if entries:
        entry = entries[0]
        print(f"   Entry type: {entry['entry_type']}")
        print(f"   Content: {entry['content'][:50]}...")
        print(f"   Attitude: {entry['attitude']}")
        print(f"   Form: {entry['form']}")
        print(f"   Body: {entry['body']}")
        print(f"   Response: {entry['response']}")

    # Cleanup
    db.clear_all_user_data(test_user_id)

    print("\n" + "="*80)
    print("✓ Guided practice flow test complete")
    print("="*80 + "\n")


async def test_multiple_refinements():
    """
    Test unlimited refinements for a single field.

    Demonstrates that user can add to answer multiple times by just sending text.
    """
    print("\n" + "="*80)
    print("TEST: UNLIMITED REFINEMENTS (NO BUTTON NEEDED)")
    print("="*80 + "\n")

    # Setup
    test_user_id = 444555666
    db.init_database()
    db.ensure_user_exists(test_user_id)

    mock_bot = MockBot()
    context = MockContext(mock_bot)
    context.user_data['authenticated'] = True
    context.user_data['mode'] = 'guided_practice'
    context.user_data['current_field'] = 0
    context.user_data['practice_data'] = {}
    context.user_data['current_answer'] = None

    print("User answers field")
    update = MockUpdate("Первая версия ответа", test_user_id)
    await handle_practice_input(update, context)
    print(f"   Answer 1: {context.user_data.get('current_answer')}")
    print("   [Bot shows with 'Всё ок' button]")

    # Refinement 1 - just send more text
    print("\nUser sends more text (attempt 1) - no button needed")
    update = MockUpdate("Добавление к ответу", test_user_id)
    await handle_practice_input(update, context)
    print(f"   Answer 2: {context.user_data.get('current_answer')}")
    print("   [Bot shows accumulated answer with 'Всё ок' button]")

    # Refinement 2 - just send more text
    print("\nUser sends more text (attempt 2) - no button needed")
    update = MockUpdate("Ещё уточнение", test_user_id)
    await handle_practice_input(update, context)
    print(f"   Answer 3: {context.user_data.get('current_answer')}")
    print("   [Bot shows accumulated answer with 'Всё ок' button]")

    # Refinement 3 - just send more text
    print("\nUser sends more text (attempt 3) - no button needed")
    update = MockUpdate("И ещё одно", test_user_id)
    await handle_practice_input(update, context)
    print(f"   Answer 4: {context.user_data.get('current_answer')}")
    print("   [Bot shows accumulated answer with 'Всё ок' button]")

    # Finally confirm
    print("\nUser finally clicks 'Всё ок'")
    update = MockUpdate("", test_user_id)
    update.callback_query = MockCallbackQuery('field_ok', test_user_id)
    await handle_practice_callback(update, context)

    print(f"\n   Saved to practice_data: {context.user_data.get('practice_data')}")
    print(f"   Current answer reset: {context.user_data.get('current_answer')}")

    # Cleanup
    db.clear_all_user_data(test_user_id)

    print("\n✓ Unlimited refinements test complete (simpler flow without refine button)\n")


async def run_all_tests():
    """Run all practice handler tests."""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    print("\n" + "="*80)
    print("PRACTICE HANDLER TEST SUITE")
    print("="*80)

    # Initialize once
    db.init_database()

    try:
        await test_guided_practice_flow()
        await test_multiple_refinements()

        print("="*80)
        print("ALL PRACTICE HANDLER TESTS PASSED ✓")
        print("="*80)
        print()

    except Exception as e:
        print(f"\n✗ Test failed with error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == '__main__':
    asyncio.run(run_all_tests())
