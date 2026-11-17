"""Force Subscribe verification service."""

from dataclasses import dataclass
from typing import Any, Dict, Optional
from aiogram import Bot
from aiogram.enums import ChatMemberStatus
from aiogram.exceptions import TelegramBadRequest, TelegramForbiddenError
from config import settings
from database.join_requests import JoinRequestRepository
from database.subscriptions import SubscriptionRepository
from utils.logger import logger


@dataclass
class SubscriptionCheckResult:
    """Detailed verification outcome."""
    is_fully_satisfied: bool
    sub1_satisfied: bool
    sub2_satisfied: bool
    sub2_info: Optional[Dict[str, Any]] = None


class ForceSubService:
    """Service handling multi-channel subscription verification."""

    VALID_STATUSES = {
        ChatMemberStatus.CREATOR,
        ChatMemberStatus.ADMINISTRATOR,
        ChatMemberStatus.MEMBER,
    }

    @classmethod
    async def is_member_of_chat(cls, bot: Bot, chat_id: int, user_id: int) -> bool:
        """Check if user has active membership in a given chat/channel."""
        try:
            member = await bot.get_chat_member(chat_id=chat_id, user_id=user_id)
            if member.status in cls.VALID_STATUSES:
                return True
            if member.status == ChatMemberStatus.RESTRICTED and getattr(member, "is_member", False):
                return True
            return False
        except (TelegramBadRequest, TelegramForbiddenError) as e:
            logger.debug(
                "Chat member lookup failed for user %d in chat %d: %s",
                user_id,
                chat_id,
                e,
            )
            return False
        except Exception as e:
            logger.error(
                "Unexpected error checking chat membership (chat=%d, user=%d): %s",
                chat_id,
                user_id,
                e,
            )
            return False

    @classmethod
    async def verify_user_subscription(
        cls,
        bot: Bot,
        user_id: int,
    ) -> SubscriptionCheckResult:
        """Verify user status against Sub 1 (Fixed) and Sub 2 (Dynamic)."""
        # 1. Verify Sub 1 (Permanent Main Movie Channel)
        sub1_satisfied = False
        if settings.SUB1_CHANNEL_ID:
            sub1_satisfied = await cls.is_member_of_chat(
                bot=bot,
                chat_id=settings.SUB1_CHANNEL_ID,
                user_id=user_id,
            )
        else:
            # If not configured in dev/testing, default to True
            sub1_satisfied = True

        # 2. Verify Sub 2 (Dynamic Additional Channel from MongoDB)
        sub2_info = await SubscriptionRepository.get_sub2()
        sub2_satisfied = True  # Default satisfied if Sub 2 disabled or not configured

        if sub2_info and sub2_info.get("is_enabled", False):
            sub2_channel_id = sub2_info.get("channel_id")
            channel_type = sub2_info.get("channel_type", "public")

            if channel_type == "public":
                # Public channel: user must be active member via getChatMember
                sub2_satisfied = await cls.is_member_of_chat(
                    bot=bot,
                    chat_id=sub2_channel_id,
                    user_id=user_id,
                )
            elif channel_type == "private_request":
                # Private channel with Join Request:
                # 1) Check if join request was recorded in MongoDB
                has_req = await JoinRequestRepository.has_join_request(
                    user_id=user_id,
                    channel_id=sub2_channel_id,
                )
                if has_req:
                    sub2_satisfied = True
                else:
                    # 2) Fallback: user might already be an approved member
                    is_member = await cls.is_member_of_chat(
                        bot=bot,
                        chat_id=sub2_channel_id,
                        user_id=user_id,
                    )
                    sub2_satisfied = is_member

        is_fully_satisfied = sub1_satisfied and sub2_satisfied

        return SubscriptionCheckResult(
            is_fully_satisfied=is_fully_satisfied,
            sub1_satisfied=sub1_satisfied,
            sub2_satisfied=sub2_satisfied,
            sub2_info=sub2_info,
        )
