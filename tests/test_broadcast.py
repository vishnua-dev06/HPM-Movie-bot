"""Unit and integration tests for the Advanced High-Performance Broadcast Engine."""

import asyncio
from unittest.mock import AsyncMock, MagicMock
import pytest
from aiogram.exceptions import (
    TelegramBadRequest,
    TelegramForbiddenError,
    TelegramNetworkError,
    TelegramRetryAfter,
)
from database.broadcast_recipients import BroadcastRecipientRepository
from database.broadcasts import BroadcastRepository
from database.users import UserRepository
from services.broadcast_service import BroadcastService


@pytest.mark.asyncio
async def test_text_and_photo_single_delivery():
    """Verify delivery of single message types using copy_message."""
    bot = AsyncMock()

    messages = [
        {"source_chat_id": 12345, "source_message_id": 10, "media_type": "text", "caption": "Hello!"},
    ]

    status, err = await BroadcastService.deliver_messages_to_user(bot, user_id=9001, messages=messages)

    assert status == "successful"
    assert err is None
    bot.copy_message.assert_called_once_with(chat_id=9001, from_chat_id=12345, message_id=10)


@pytest.mark.asyncio
async def test_multiple_messages_and_album_delivery():
    """Verify delivery of multiple messages and album media groups."""
    bot = AsyncMock()

    messages = [
        {"source_chat_id": 100, "source_message_id": 1, "media_type": "photo", "media_group_id": "album_1"},
        {"source_chat_id": 100, "source_message_id": 2, "media_type": "photo", "media_group_id": "album_1"},
        {"source_chat_id": 100, "source_message_id": 3, "media_type": "video", "media_group_id": None},
    ]

    status, err = await BroadcastService.deliver_messages_to_user(bot, user_id=9002, messages=messages)

    assert status == "successful"
    # copy_messages should be called once for the album
    bot.copy_messages.assert_called_once_with(
        chat_id=9002,
        from_chat_id=100,
        message_ids=[1, 2],
    )
    # copy_message should be called once for the independent video
    bot.copy_message.assert_called_once_with(
        chat_id=9002,
        from_chat_id=100,
        message_id=3,
    )


@pytest.mark.asyncio
async def test_blocked_user_detection_and_flagging():
    """Verify TelegramForbiddenError is caught and marks user as blocked in MongoDB."""
    bot = AsyncMock()
    bot.copy_message.side_effect = TelegramForbiddenError(method=MagicMock(), message="Forbidden: bot was blocked by the user")

    # Register active user first
    await UserRepository.upsert_user(user_id=9003, username="blocker", first_name="User")
    user_before = await UserRepository.get_user(9003)
    assert user_before["is_blocked"] is False

    messages = [{"source_chat_id": 100, "source_message_id": 1, "media_type": "text"}]

    status, err = await BroadcastService.deliver_messages_to_user(bot, user_id=9003, messages=messages)

    assert status == "blocked"
    # Check user record in database
    user_after = await UserRepository.get_user(9003)
    assert user_after["is_blocked"] is True
    assert user_after["status"] == "blocked"


@pytest.mark.asyncio
async def test_retry_after_handling():
    """Verify that TelegramRetryAfter pauses and succeeds on subsequent retry."""
    bot = AsyncMock()
    # First call raises RetryAfter, second call succeeds
    retry_exc = TelegramRetryAfter(method=MagicMock(), message="Flood control exceeded", retry_after=0.01)
    bot.copy_message.side_effect = [retry_exc, MagicMock()]

    messages = [{"source_chat_id": 100, "source_message_id": 1, "media_type": "text"}]

    status, err = await BroadcastService.deliver_messages_to_user(bot, user_id=9004, messages=messages)

    assert status == "successful"
    assert bot.copy_message.call_count == 2


@pytest.mark.asyncio
async def test_full_broadcast_engine_execution_and_metrics():
    """Verify end-to-end broadcast execution over multiple recipients."""
    bot = AsyncMock()

    # Seed 5 users
    for i in range(1, 6):
        await UserRepository.upsert_user(user_id=8000 + i, username=f"user_{i}", first_name=f"Name {i}")

    messages = [{"source_chat_id": 500, "source_message_id": 99, "media_type": "text"}]

    broadcast_id = await BroadcastService.start_broadcast(
        bot=bot,
        admin_id=999999999,
        messages=messages,
    )

    # Allow background worker to complete
    await asyncio.sleep(0.2)

    job = await BroadcastRepository.get_broadcast_job(broadcast_id)
    assert job is not None
    assert job["status"] == "completed"
    assert job["successful"] == 5
    assert job["failed"] == 0
    assert job["remaining"] == 0


@pytest.mark.asyncio
async def test_broadcast_recovery_after_restart():
    """Verify that interrupted broadcast jobs resume and complete remaining recipients."""
    bot = AsyncMock()

    messages = [{"source_chat_id": 500, "source_message_id": 99, "media_type": "text"}]

    # Create job directly in "in_progress" state simulating crash
    broadcast_id = await BroadcastRepository.create_broadcast_job(
        created_by=999999999,
        total_recipients=3,
        messages=messages,
    )
    await BroadcastRepository.mark_started(broadcast_id)

    # Insert 3 recipients: 1 already delivered, 2 pending
    await BroadcastRecipientRepository.update_recipient_status(broadcast_id, user_id=7001, status="successful")
    await BroadcastRecipientRepository.insert_recipients_batch(broadcast_id, [7002, 7003])

    # Run recovery
    resumed = await BroadcastService.resume_interrupted_broadcasts(bot)
    assert resumed == 1

    # Allow worker to finish
    await asyncio.sleep(0.2)

    counts = await BroadcastRecipientRepository.get_counts_by_status(broadcast_id)
    assert counts["successful"] == 3
    assert counts["pending"] == 0
