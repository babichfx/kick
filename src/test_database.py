"""
Quick test script for database operations.
"""

import database as db

def test_database():
    """Test basic database operations."""
    print("Testing database operations...\n")

    # Test user ID
    test_user_id = 123456789

    # 1. Test user creation
    print("1. Creating user...")
    db.ensure_user_exists(test_user_id)
    user = db.get_user(test_user_id)
    assert user is not None, "User creation failed"
    print(f"   ✓ User created: {user['telegram_user_id']}")

    # 2. Test authentication
    print("\n2. Testing authentication...")
    assert not db.is_user_authenticated(test_user_id), "User should not be authenticated initially"
    db.update_user_auth(test_user_id, True)
    assert db.is_user_authenticated(test_user_id), "User authentication update failed"
    print("   ✓ Authentication works correctly")

    # 3. Test reminder schedule
    print("\n3. Testing reminder schedule...")
    schedule = {
        "times": ["09:00", "13:00", "17:00", "21:00"],
        "day_filter": "weekdays",
        "timezone": "Europe/Moscow"
    }
    db.set_reminder_schedule(test_user_id, schedule)
    retrieved_schedule = db.get_reminder_schedule(test_user_id)
    assert retrieved_schedule == schedule, "Schedule retrieval failed"
    print(f"   ✓ Reminder schedule saved and retrieved: {retrieved_schedule['times']}")

    # 4. Test structured practice entry (first)
    print("\n4. Testing structured practice entry (first)...")
    entry_id = db.create_entry(
        telegram_user_id=test_user_id,
        content='Тревога по поводу встречи',
        attitude='Напряжение в груди',
        form='Нет-отвергающее',
        body='Да, совпадает',
        response='Напряжение немного уменьшилось'
    )
    print(f"   ✓ Structured entry created with ID: {entry_id}")

    # 5. Test structured practice entry (second)
    print("\n5. Testing structured practice entry (second)...")
    entry_id = db.create_entry(
        telegram_user_id=test_user_id,
        content='Радость от завершения проекта',
        attitude='Расслабление в теле',
        form='Да-принимающее',
        body='Да, совпадает',
        response='Энергия увеличилась'
    )
    print(f"   ✓ Structured entry created with ID: {entry_id}")

    # 6. Test entry retrieval
    print("\n6. Testing entry retrieval...")
    entries = db.get_user_entries(test_user_id)
    assert len(entries) == 2, f"Expected 2 entries, found {len(entries)}"
    print(f"   ✓ Retrieved {len(entries)} entries")
    for i, entry in enumerate(entries, 1):
        print(f"     - Entry {i}: {entry['content'][:30]}... at {entry['date']}")

    # 7. Test refusal
    print("\n7. Testing refusal tracking...")
    refusal_id = db.create_refusal(test_user_id)
    refusals = db.get_user_refusals(test_user_id)
    assert len(refusals) == 1, "Refusal tracking failed"
    print(f"   ✓ Refusal recorded with ID: {refusal_id}")

    # 8. Test data isolation (create another user)
    print("\n8. Testing multi-user data isolation...")
    test_user_id_2 = 987654321
    db.ensure_user_exists(test_user_id_2)
    db.create_entry(
        telegram_user_id=test_user_id_2,
        content='Different user content',
        attitude='Different user attitude',
        form='Да-принимающее',
        body='Нет, не совпадает',
        response='Different user response'
    )
    user1_entries = db.get_user_entries(test_user_id)
    user2_entries = db.get_user_entries(test_user_id_2)
    assert len(user1_entries) == 2, "User 1 should have 2 entries"
    assert len(user2_entries) == 1, "User 2 should have 1 entry"
    print("   ✓ Data isolation working correctly")
    print(f"     - User 1: {len(user1_entries)} entries")
    print(f"     - User 2: {len(user2_entries)} entries")

    # 9. Test data cleanup
    print("\n9. Testing data cleanup...")
    db.clear_all_user_data(test_user_id)
    db.clear_all_user_data(test_user_id_2)
    entries_after_cleanup = db.get_user_entries(test_user_id)
    assert len(entries_after_cleanup) == 0, "Data cleanup failed"
    print("   ✓ All test data cleaned up successfully")

    print("\n" + "="*50)
    print("All database tests passed! ✓")
    print("="*50)


if __name__ == '__main__':
    test_database()
