"""Advanced High-Performance Broadcast Engine with persistent state, rate limiting, and crash recovery."""

import asyncio
import time
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple
from bson import ObjectId
from aiogram import Bot
from aiogram.exceptions import (
    TelegramBadRequest,
    TelegramForbiddenError,
    TelegramNetworkError,
    TelegramRetryAfter,
)
from aiogram.types import Message
from config import settings
from database.broadcast_recipients import BroadcastRecipientRepository
from database.broadcasts import BroadcastRepository
from database.users import UserRepository
from utils.helpers import format_number
from utils.logger import logger


class BroadcastService:
    """Enterprise broadcast engine designed for 100,000–300,000 registered users with durable MongoDB state."""

    _active_broadcast_task: Optional[asyncio.Task] = None

    @staticmethod
    def extract_message_info(message: Message) -> Dict[str, Any]:
        """Extract all Telegram message metadata for copying without downloading files."""
        media_type = "text"
        if message.photo:
            media_type = "photo"
        elif message.video:
            media_type = "video"
        elif message.document:
            media_type = "document"
        elif message.audio:
            media_type = "audio"
        elif message.voice:
            media_type = "voice"
        elif message.animation:
            media_type = "animation"
        elif message.sticker:
            media_type = "sticker"

        caption = message.caption or message.text or ""

        return {
            "source_chat_id": message.chat.id,
            "source_message_id": message.message_id,
            "media_group_id": message.media_group_id,
            "media_type": media_type,
            "caption": caption,
        }

    @classmethod
    async def deliver_messages_to_user(
        cls,
        bot: Bot,
        user_id: int,
        messages: List[Dict[str, Any]],
        max_retries: int = 3,
    ) -> Tuple[str, Optional[str]]:
        """Deliver all collected broadcast messages to a single recipient using Telegram copy APIs."""
        # Group consecutive album messages if present
        grouped: List[List[Dict[str, Any]]] = []
        current_grp: List[Dict[str, Any]] = []
        current_grp_id: Optional[str] = None

        for m in messages:
            grp_id = m.get("media_group_id")
            if grp_id:
                if grp_id == current_grp_id:
                    current_grp.append(m)
                else:
                    if current_grp:
                        grouped.append(current_grp)
                    current_grp = [m]
                    current_grp_id = grp_id
            else:
                if current_grp:
                    grouped.append(current_grp)
                    current_grp = []
                    current_grp_id = None
                grouped.append([m])

        if current_grp:
            grouped.append(current_grp)

        for batch in grouped:
            for attempt in range(max_retries):
                try:
                    if len(batch) > 1 and all(b.get("source_chat_id") == batch[0].get("source_chat_id") for b in batch):
                        # Multi-item album
                        await bot.copy_messages(
                            chat_id=user_id,
                            from_chat_id=batch[0]["source_chat_id"],
                            message_ids=[b["source_message_id"] for b in batch],
                        )
                    else:
                        # Individual messages
                        for item in batch:
                            await bot.copy_message(
                                chat_id=user_id,
                                from_chat_id=item["source_chat_id"],
                                message_id=item["source_message_id"],
                            )
                    return "successful", None

                except TelegramForbiddenError:
                    # User blocked the bot
                    await UserRepository.mark_user_blocked(user_id)
                    return "blocked", "User blocked bot"

                except TelegramRetryAfter as e:
                    logger.warning("Telegram flood control: sleeping %s seconds for user %d", e.retry_after, user_id)
                    await asyncio.sleep(e.retry_after + 0.1)

                except (TelegramNetworkError, asyncio.TimeoutError) as net_err:
                    backoff = (2 ** attempt) * 0.5
                    logger.warning("Network issue delivering to %d (attempt %d): %s. Backoff %s s", user_id, attempt + 1, net_err, backoff)
                    await asyncio.sleep(backoff)

                except TelegramBadRequest as bad_req:
                    # Permanent bad request (e.g. chat not found)
                    return "failed", str(bad_req)

                except Exception as e:
                    logger.error("Unhandled delivery error for user %d: %s", user_id, e)
                    return "failed", str(e)

        return "failed", "Max retries exceeded"

    @classmethod
    async def start_broadcast(
        cls,
        bot: Bot,
        admin_id: int,
        messages: List[Dict[str, Any]],
        status_message: Optional[Message] = None,
    ) -> ObjectId:
        """Create durable broadcast job and spawn the background worker."""
        total_recipients = await UserRepository.get_active_users_count()

        broadcast_id = await BroadcastRepository.create_broadcast_job(
            created_by=admin_id,
            total_recipients=total_recipients,
            messages=messages,
        )

        # Launch worker in background
        task = asyncio.create_task(
            cls._broadcast_worker(
                bot=bot,
                broadcast_id=broadcast_id,
                admin_id=admin_id,
                status_message=status_message,
            )
        )
        cls._active_broadcast_task = task
        return broadcast_id

    @classmethod
    async def _broadcast_worker(
        cls,
        bot: Bot,
        broadcast_id: ObjectId,
        admin_id: int,
        status_message: Optional[Message] = None,
    ) -> None:
        """Core background broadcast worker streaming recipients in batches."""
        start_time = time.monotonic()
        await BroadcastRepository.mark_started(broadcast_id)

        job = await BroadcastRepository.get_broadcast_job(broadcast_id)
        if not job:
            return

        messages = job.get("messages", [])
        total_recipients = job.get("total_recipients", 0)

        successful_count = 0
        failed_count = 0
        blocked_count = 0
        processed_count = 0

        # Concurrency limiter
        concurrency = max(1, min(settings.BROADCAST_CONCURRENCY, 30))
        semaphore = asyncio.Semaphore(concurrency)
        last_progress_edit = time.monotonic()

        logger.info(
            "Broadcast #%s started: %d users target, concurrency=%d, batch_size=%d",
            broadcast_id,
            total_recipients,
            concurrency,
            settings.BROADCAST_BATCH_SIZE,
        )

        async def process_single_user(uid: int):
            nonlocal successful_count, failed_count, blocked_count, processed_count
            async with semaphore:
                status, err_msg = await cls.deliver_messages_to_user(bot, uid, messages)
                if status == "successful":
                    successful_count += 1
                elif status == "blocked":
                    blocked_count += 1
                    failed_count += 1
                else:
                    failed_count += 1

                processed_count += 1

                # Record recipient status in MongoDB
                await BroadcastRecipientRepository.update_recipient_status(
                    broadcast_id=broadcast_id,
                    user_id=uid,
                    status=status,
                    error_message=err_msg,
                )

                # Rate pacing
                if settings.BROADCAST_DELAY_SECONDS > 0:
                    await asyncio.sleep(settings.BROADCAST_DELAY_SECONDS)

        # Stream active user IDs from database in chunks of BROADCAST_BATCH_SIZE
        async for user_batch in UserRepository.stream_active_user_ids_in_batches(batch_size=settings.BROADCAST_BATCH_SIZE):
            # Seed recipient records in MongoDB
            await BroadcastRecipientRepository.insert_recipients_batch(broadcast_id, user_batch)

            # Process chunk concurrently under semaphore
            tasks = [asyncio.create_task(process_single_user(uid)) for uid in user_batch]
            await asyncio.gather(*tasks)

            # Persist live progress to MongoDB
            remaining = max(0, total_recipients - processed_count)
            await BroadcastRepository.update_progress(
                broadcast_id=broadcast_id,
                processed=processed_count,
                successful=successful_count,
                failed=failed_count,
                remaining=remaining,
            )

            # Throttle progress edits to Telegram message (every 5 seconds max)
            now = time.monotonic()
            if status_message and (now - last_progress_edit >= 5.0):
                last_progress_edit = now
                try:
                    progress_text = (
                        "📢 <b>BROADCAST IN PROGRESS</b>\n\n"
                        f"• <b>Total Users:</b> {format_number(total_recipients)}\n"
                        f"• <b>Processed:</b> {format_number(processed_count)}\n"
                        f"• <b>Successful:</b> {format_number(successful_count)}\n"
                        f"• <b>Failed / Blocked:</b> {format_number(failed_count)}\n"
                        f"• <b>Remaining:</b> {format_number(remaining)}\n\n"
                        "<i>Delivering with controlled concurrency and flood protection...</i>"
                    )
                    await status_message.edit_text(progress_text, parse_mode="HTML")
                except Exception:
                    pass

        # Final duration
        total_duration = time.monotonic() - start_time
        mins, secs = divmod(int(total_duration), 60)
        duration_str = f"{mins}m {secs}s" if mins > 0 else f"{secs}s"

        await BroadcastRepository.complete_broadcast_job(
            broadcast_id=broadcast_id,
            successful=successful_count,
            failed=failed_count,
            total_recipients=total_recipients,
            duration_str=duration_str,
        )

        # Final Completion Report
        report_text = (
            "🎉 <b>BROADCAST COMPLETED</b>\n\n"
            f"• <b>Total Recipients:</b> {format_number(total_recipients)}\n"
            f"• <b>Successful Deliveries:</b> {format_number(successful_count)}\n"
            f"• <b>Failed Deliveries:</b> {format_number(failed_count)}\n"
            f"• <b>Blocked Bots Flagged:</b> {format_number(blocked_count)}\n"
            f"• <b>Skipped:</b> 0\n"
            f"• <b>Processing Duration:</b> {duration_str}\n\n"
            "<i>All recipient records and metrics are safely stored in MongoDB.</i>"
        )

        try:
            if status_message:
                await status_message.edit_text(report_text, parse_mode="HTML")
            else:
                await bot.send_message(chat_id=admin_id, text=report_text, parse_mode="HTML")
        except Exception:
            try:
                await bot.send_message(chat_id=admin_id, text=report_text, parse_mode="HTML")
            except Exception:
                pass

        logger.info(
            "Broadcast #%s completed in %s. Success: %d, Failed: %d",
            broadcast_id,
            duration_str,
            successful_count,
            failed_count,
        )

    @classmethod
    async def resume_interrupted_broadcasts(cls, bot: Bot) -> int:
        """Scan MongoDB for any broadcast jobs that were interrupted by a server restart and resume them."""
        unfinished = await BroadcastRepository.get_unfinished_broadcasts()
        if not unfinished:
            return 0

        logger.info("Found %d interrupted broadcast job(s) to recover.", len(unfinished))
        resumed_count = 0

        for job in unfinished:
            broadcast_id = job["_id"]
            admin_id = job.get("created_by", settings.primary_admin_id)

            logger.info("Resuming interrupted broadcast #%s...", broadcast_id)
            asyncio.create_task(
                cls._resume_worker(bot=bot, broadcast_id=broadcast_id, admin_id=admin_id)
            )
            resumed_count += 1

        return resumed_count

    @classmethod
    async def _resume_worker(cls, bot: Bot, broadcast_id: ObjectId, admin_id: int) -> None:
        """Worker resuming unfinished broadcast from where it stopped."""
        job = await BroadcastRepository.get_broadcast_job(broadcast_id)
        if not job:
            return

        messages = job.get("messages", [])
        total_recipients = job.get("total_recipients", 0)

        # Deliver to any pending recipients recorded in MongoDB
        semaphore = asyncio.Semaphore(settings.BROADCAST_CONCURRENCY)

        while True:
            pending_batch = await BroadcastRecipientRepository.get_pending_recipients_batch(
                broadcast_id=broadcast_id,
                limit=settings.BROADCAST_BATCH_SIZE,
            )
            if not pending_batch:
                break

            async def process_one(uid: int):
                async with semaphore:
                    status, err_msg = await cls.deliver_messages_to_user(bot, uid, messages)
                    await BroadcastRecipientRepository.update_recipient_status(
                        broadcast_id=broadcast_id,
                        user_id=uid,
                        status=status,
                        error_message=err_msg,
                    )

            tasks = [asyncio.create_task(process_one(uid)) for uid in pending_batch]
            await asyncio.gather(*tasks)

        # Check final stats
        counts = await BroadcastRecipientRepository.get_counts_by_status(broadcast_id)
        await BroadcastRepository.complete_broadcast_job(
            broadcast_id=broadcast_id,
            successful=counts.get("successful", 0),
            failed=counts.get("failed", 0) + counts.get("blocked", 0),
            total_recipients=total_recipients,
            duration_str="Resumed after restart",
        )

        try:
            await bot.send_message(
                chat_id=admin_id,
                text=(
                    f"🔄 <b>Interrupted Broadcast #<code>{broadcast_id}</code> Successfully Resumed & Completed!</b>\n\n"
                    f"• <b>Successful:</b> {format_number(counts.get('successful', 0))}\n"
                    f"• <b>Failed:</b> {format_number(counts.get('failed', 0) + counts.get('blocked', 0))}"
                ),
                parse_mode="HTML",
            )
        except Exception:
            pass
