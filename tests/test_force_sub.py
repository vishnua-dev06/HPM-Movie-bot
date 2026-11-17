"""Automated test suite for Force Subscribe verification combinations."""

from unittest.mock import AsyncMock, MagicMock
import pytest
from aiogram.enums import ChatMemberStatus
from config import settings
from database.join_requests import JoinRequestRepository
from database.subscriptions import SubscriptionRepository
from services.force_sub import ForceSubService


def make_mock_bot(sub1_is_member: bool, sub2_is_member: bool = False):
    """Factory creating a mock Bot with get_chat_member responses."""
    bot = AsyncMock()

    async def get_chat_member(chat_id: int, user_id: int):
        mock_member = MagicMock()
        if chat_id == settings.SUB1_CHANNEL_ID:
            mock_member.status = ChatMemberStatus.MEMBER if sub1_is_member else ChatMemberStatus.LEFT
        else:
            mock_member.status = ChatMemberStatus.MEMBER if sub2_is_member else ChatMemberStatus.LEFT
        return mock_member

    bot.get_chat_member = AsyncMock(side_effect=get_chat_member)
    return bot


@pytest.mark.asyncio
async def test_combination_1_sub1_joined_sub2_joined_access_allowed():
    """Combination 1: Sub 1 joined + Sub 2 joined = Access allowed."""
    sub2_channel_id = -1002222222222
    await SubscriptionRepository.set_sub2(
        channel_id=sub2_channel_id,
        channel_type="public",
        invite_url="https://t.me/sub2_public",
        is_enabled=True,
    )

    bot = make_mock_bot(sub1_is_member=True, sub2_is_member=True)
    user_id = 1001

    result = await ForceSubService.verify_user_subscription(bot=bot, user_id=user_id)

    assert result.sub1_satisfied is True
    assert result.sub2_satisfied is True
    assert result.is_fully_satisfied is True


@pytest.mark.asyncio
async def test_combination_2_sub1_not_joined_sub2_joined_access_denied():
    """Combination 2: Sub 1 not joined + Sub 2 joined = Access denied."""
    sub2_channel_id = -1002222222222
    await SubscriptionRepository.set_sub2(
        channel_id=sub2_channel_id,
        channel_type="public",
        invite_url="https://t.me/sub2_public",
        is_enabled=True,
    )

    bot = make_mock_bot(sub1_is_member=False, sub2_is_member=True)
    user_id = 1002

    result = await ForceSubService.verify_user_subscription(bot=bot, user_id=user_id)

    assert result.sub1_satisfied is False
    assert result.sub2_satisfied is True
    assert result.is_fully_satisfied is False


@pytest.mark.asyncio
async def test_combination_3_sub1_joined_public_sub2_not_joined_access_denied():
    """Combination 3: Sub 1 joined + Public Sub 2 not joined = Access denied."""
    sub2_channel_id = -1002222222222
    await SubscriptionRepository.set_sub2(
        channel_id=sub2_channel_id,
        channel_type="public",
        invite_url="https://t.me/sub2_public",
        is_enabled=True,
    )

    bot = make_mock_bot(sub1_is_member=True, sub2_is_member=False)
    user_id = 1003

    result = await ForceSubService.verify_user_subscription(bot=bot, user_id=user_id)

    assert result.sub1_satisfied is True
    assert result.sub2_satisfied is False
    assert result.is_fully_satisfied is False


@pytest.mark.asyncio
async def test_combination_4_sub1_joined_private_sub2_request_recorded_access_allowed():
    """Combination 4: Sub 1 joined + Private Sub 2 request recorded = Access allowed."""
    sub2_channel_id = -1003333333333
    await SubscriptionRepository.set_sub2(
        channel_id=sub2_channel_id,
        channel_type="private_request",
        invite_url="https://t.me/+join_req_link",
        is_enabled=True,
    )

    user_id = 1004

    # Simulate ChatJoinRequest recorded in MongoDB
    await JoinRequestRepository.record_join_request(
        user_id=user_id,
        channel_id=sub2_channel_id,
    )

    bot = make_mock_bot(sub1_is_member=True, sub2_is_member=False)

    result = await ForceSubService.verify_user_subscription(bot=bot, user_id=user_id)

    assert result.sub1_satisfied is True
    assert result.sub2_satisfied is True  # Satisfied via recorded join request!
    assert result.is_fully_satisfied is True


@pytest.mark.asyncio
async def test_combination_5_sub1_joined_sub2_disabled_access_allowed():
    """Combination 5: Sub 1 joined + Sub 2 disabled = Access allowed."""
    sub2_channel_id = -1004444444444
    await SubscriptionRepository.set_sub2(
        channel_id=sub2_channel_id,
        channel_type="public",
        invite_url="https://t.me/sub2_disabled",
        is_enabled=False,  # Sub 2 is DISABLED
    )

    bot = make_mock_bot(sub1_is_member=True, sub2_is_member=False)
    user_id = 1005

    result = await ForceSubService.verify_user_subscription(bot=bot, user_id=user_id)

    assert result.sub1_satisfied is True
    assert result.sub2_satisfied is True  # Skipped because disabled
    assert result.is_fully_satisfied is True


@pytest.mark.asyncio
async def test_combination_6_sub1_not_joined_sub2_disabled_access_denied():
    """Combination 6: Sub 1 not joined + Sub 2 disabled = Access denied."""
    sub2_channel_id = -1004444444444
    await SubscriptionRepository.set_sub2(
        channel_id=sub2_channel_id,
        channel_type="public",
        invite_url="https://t.me/sub2_disabled",
        is_enabled=False,  # Sub 2 is DISABLED
    )

    bot = make_mock_bot(sub1_is_member=False, sub2_is_member=False)
    user_id = 1006

    result = await ForceSubService.verify_user_subscription(bot=bot, user_id=user_id)

    assert result.sub1_satisfied is False
    assert result.sub2_satisfied is True  # Skipped
    assert result.is_fully_satisfied is False
