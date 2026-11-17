"""Controlled asynchronous broadcast worker."""

import asyncio
from typing import Any, Dict
from aiogram import Bot
from aiogram.exceptions import TelegramForbiddenError, TelegramRetryAfter
from config import settings
from database.broadcasts import BroadcastRepository
from database.users import UserRepository
from utils.logger import logger


class BroadcastService:
    """Service executing rate-limited message broadcasts to registered users."""

    @classmethod
    async def run_broadcast(
        cls,
        bot: Bot,
        admin_id: int,
        source_chat_id: int,
        source_message_id: int,
    ) -> Dict[str, Any]:
        """Broadcast a message to all active users with rate limiting and error handling."""
        user_ids = await UserRepository.get_all_active_user_ids()
        total_users = len(user_ids)

        broadcast_id = await BroadcastRepository.create_broadcast(
            admin_id=admin_id,
            total_users=total_users,
        )

        success_count = 0
        failed_count = 0
        blocked_count = 0

        logger.info(
            "Starting broadcast #%s to %d users from chat %d msg %d",
            broadcast_id,
            total_users,
            source_chat_id,
            source_message_id,
        )

        for idx, uid in enumerate(user_ids):
            try:
                await bot.copy_message(
                    chat_id=uid,
                    from_chat_id=source_chat_id,
                    message_id=source_message_id,
                )
                success_count += 1
            except TelegramForbiddenError:
                # User has blocked the bot
                blocked_count += 1
                await UserRepository.set_user_status(uid, "blocked")
            except TelegramRetryAfter as e:
                logger.warning("Telegram flood limit reached during broadcast. Sleeping %s s", e.retry_after)
                await asyncio.sleep(e.retry_after)
                # Retry once
                try:
                    await bot.copy_message(
                        chat_id=uid,
                        from_chat_id=source_chat_id,
                        message_id=source_message_id,
                    )
                    success_count += 1
                except Exception:
                    failed_count += 1
            except Exception as e:
                logger.error("Failed to deliver broadcast to user %d: %s", uid, e)
                failed_count += 1

            # Rate limit pacing
            await asyncio.sleep(settings.BROADCAST_DELAY_SECONDS)

        # Complete broadcast metrics
        await BroadcastRepository.complete_broadcast(
            broadcast_id=broadcast_id,
            success_count=success_count,
            failed_count=failed_count,
            blocked_count=blocked_count,
        )

        logger.info(
            "Broadcast #%s completed. Total: %d, Success: %d, Failed: %d, Blocked: %d",
            broadcast_id,
            total_users,
            success_count,
            failed_count,
            blocked_count,
        )

        return {
            "total_users": total_users,
            "success_count": success_count,
            "failed_count": failed_count,
            "blocked_count": blocked_count,
        }
