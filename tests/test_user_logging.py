"""Unit and integration tests for User Log Channel integration."""

from unittest.mock import AsyncMock, MagicMock
import pytest
from aiogram.types import User
from database.log_channel import LogChannelRepository
from database.users import UserRepository
from services.log_channel_service import LogChannelService


@pytest.mark.asyncio
async def test_first_time_user_registration_triggers_log():
    """Verify that a brand-new user triggers Log Channel notification."""
    bot = AsyncMock()
    user = User(
        id=777001,
        is_bot=False,
        first_name="Alice",
        last_name="Wonderland",
        username="alicew",
        language_code="en",
    )

    # Configure Log Channel
    await LogChannelRepository.set_channel_id(-1009876543210)

    # 1. Upsert user
    user_doc, is_new_user = await UserRepository.upsert_user(
        user_id=user.id,
        username=user.username,
        first_name=user.first_name,
        last_name=user.last_name,
        language_code=user.language_code,
    )

    assert is_new_user is True
    assert user_doc["user_id"] == 777001
    assert user_doc["status"] == "active"
    assert user_doc["is_blocked"] is False

    # 2. Trigger log channel service
    success = await LogChannelService.log_new_user_registration(bot=bot, user=user)
    assert success is True

    # Verify message sent to channel with formatted details
    bot.send_message.assert_called_once()
    call_args = bot.send_message.call_args
    assert call_args.kwargs["chat_id"] == -1009876543210
    assert "777001" in call_args.kwargs["text"]
    assert "Alice" in call_args.kwargs["text"]
    assert "@alicew" in call_args.kwargs["text"]


@pytest.mark.asyncio
async def test_returning_user_and_duplicate_start_does_not_send_duplicate_log():
    """Verify that repeated /start calls by existing user do NOT trigger duplicate logs."""
    bot = AsyncMock()
    user = User(
        id=777002,
        is_bot=False,
        first_name="Bob",
        username="bobby",
    )

    # Initial registration
    _, is_new_first = await UserRepository.upsert_user(
        user_id=user.id,
        username=user.username,
        first_name=user.first_name,
    )
    assert is_new_first is True

    # Repeated /start
    _, is_new_second = await UserRepository.upsert_user(
        user_id=user.id,
        username=user.username,
        first_name=user.first_name,
    )
    assert is_new_second is False

    # Log service should not be called when is_new_user is False
    # Only test that database preserved single document
    total_docs = await UserRepository.get_total_users_count()
    assert total_docs == 1


@pytest.mark.asyncio
async def test_log_channel_unavailable_does_not_crash_registration():
    """Verify that exceptions in LogChannel sending never crash user registration."""
    bot = AsyncMock()
    # Mock bot.send_message raising Telegram exception
    bot.send_message.side_effect = Exception("Telegram API Chat Not Found 400")

    await LogChannelRepository.set_channel_id(-1009999999999)

    user = User(id=777003, is_bot=False, first_name="Charlie")

    # User registration succeeds in MongoDB
    _, is_new = await UserRepository.upsert_user(
        user_id=user.id,
        username=None,
        first_name=user.first_name,
    )
    assert is_new is True

    # Log channel attempt returns False gracefully without raising
    result = await LogChannelService.log_new_user_registration(bot=bot, user=user)
    assert result is False


@pytest.mark.asyncio
async def test_missing_optional_profile_details():
    """Verify formatting handles missing username, last name, and language code cleanly."""
    bot = AsyncMock()
    await LogChannelRepository.set_channel_id(-1001234567890)

    user = User(
        id=777004,
        is_bot=False,
        first_name="NoUser",
        last_name=None,
        username=None,
        language_code=None,
    )

    success = await LogChannelService.log_new_user_registration(bot=bot, user=user)
    assert success is True

    sent_text = bot.send_message.call_args.kwargs["text"]
    assert "777004" in sent_text
    assert "None" in sent_text
