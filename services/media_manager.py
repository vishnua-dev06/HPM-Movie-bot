"""Media management and delivery service using Telegram copyMessage."""

import asyncio
from typing import Any, Dict, List, Optional, Tuple
from aiogram import Bot
from aiogram.exceptions import TelegramBadRequest, TelegramForbiddenError, TelegramRetryAfter
from aiogram.types import Message
from database.movie_messages import MovieMessageRepository
from utils.logger import logger


class MediaManager:
    """Handles extracting media references and delivering media to users."""

    @staticmethod
    def extract_media_info(message: Message) -> Dict[str, Any]:
        """Extract media reference attributes from an incoming Telegram message."""
        media_type = "unknown"
        file_id = None
        file_unique_id = None

        if message.photo:
            media_type = "photo"
            file_id = message.photo[-1].file_id
            file_unique_id = message.photo[-1].file_unique_id
        elif message.video:
            media_type = "video"
            file_id = message.video.file_id
            file_unique_id = message.video.file_unique_id
        elif message.document:
            media_type = "document"
            file_id = message.document.file_id
            file_unique_id = message.document.file_unique_id
        elif message.audio:
            media_type = "audio"
            file_id = message.audio.file_id
            file_unique_id = message.audio.file_unique_id
        elif message.animation:
            media_type = "animation"
            file_id = message.animation.file_id
            file_unique_id = message.animation.file_unique_id
        elif message.text:
            media_type = "text"

        caption = message.caption or message.text or ""

        return {
            "source_chat_id": message.chat.id,
            "source_message_id": message.message_id,
            "media_group_id": message.media_group_id,
            "media_type": media_type,
            "file_id": file_id,
            "file_unique_id": file_unique_id,
            "caption": caption,
        }

    @classmethod
    async def deliver_movie_media(
        cls,
        bot: Bot,
        user_id: int,
        movie_id: str,
    ) -> Tuple[int, Optional[str]]:
        """Deliver all stored movie media messages to the user using copyMessage/copyMessages."""
        messages = await MovieMessageRepository.get_messages_by_movie_id(movie_id)
        if not messages:
            return 0, "No media messages found for this movie."

        delivered_count = 0

        # Group consecutive messages by media_group_id if present
        grouped_batches: List[List[Dict[str, Any]]] = []
        current_group_id: Optional[str] = None
        current_batch: List[Dict[str, Any]] = []

        for msg in messages:
            grp_id = msg.get("media_group_id")
            if grp_id:
                if grp_id == current_group_id:
                    current_batch.append(msg)
                else:
                    if current_batch:
                        grouped_batches.append(current_batch)
                    current_batch = [msg]
                    current_group_id = grp_id
            else:
                if current_batch:
                    grouped_batches.append(current_batch)
                    current_batch = []
                    current_group_id = None
                grouped_batches.append([msg])

        if current_batch:
            grouped_batches.append(current_batch)

        # Process each batch
        for batch in grouped_batches:
            try:
                # If batch is an album (multiple items with same source_chat_id)
                if len(batch) > 1 and all(
                    b.get("source_chat_id") == batch[0].get("source_chat_id") for b in batch
                ):
                    source_chat_id = batch[0]["source_chat_id"]
                    msg_ids = [b["source_message_id"] for b in batch]
                    try:
                        await bot.copy_messages(
                            chat_id=user_id,
                            from_chat_id=source_chat_id,
                            message_ids=msg_ids,
                        )
                        delivered_count += len(batch)
                    except Exception as album_err:
                        logger.warning(
                            "copy_messages failed for album, falling back to copy_message: %s",
                            album_err,
                        )
                        for item in batch:
                            success = await cls._copy_or_send_fallback(bot, user_id, item)
                            if success:
                                delivered_count += 1
                else:
                    # Single message delivery
                    for item in batch:
                        success = await cls._copy_or_send_fallback(bot, user_id, item)
                        if success:
                            delivered_count += 1

                # Gentle pacing between deliveries
                await asyncio.sleep(0.3)

            except TelegramForbiddenError:
                logger.warning("User %d blocked bot during delivery.", user_id)
                return delivered_count, "User blocked bot."
            except Exception as e:
                logger.error("Error during media delivery batch to user %d: %s", user_id, e)

        return delivered_count, None

    @classmethod
    async def _copy_or_send_fallback(
        cls,
        bot: Bot,
        user_id: int,
        item: Dict[str, Any],
    ) -> bool:
        """Attempt copy_message; fallback to direct send by file_id if needed."""
        source_chat_id = item["source_chat_id"]
        source_message_id = item["source_message_id"]

        for attempt in range(2):
            try:
                await bot.copy_message(
                    chat_id=user_id,
                    from_chat_id=source_chat_id,
                    message_id=source_message_id,
                )
                return True
            except TelegramRetryAfter as e:
                logger.info("Rate limit hit, sleeping for %s seconds", e.retry_after)
                await asyncio.sleep(e.retry_after)
            except TelegramBadRequest as bad_req:
                logger.warning(
                    "copy_message failed (%s), attempting file_id fallback for type %s",
                    bad_req,
                    item.get("media_type"),
                )
                return await cls._send_by_file_id_fallback(bot, user_id, item)
            except Exception as e:
                logger.error("Unhandled error copying message %d: %s", source_message_id, e)
                return False
        return False

    @classmethod
    async def _send_by_file_id_fallback(
        cls,
        bot: Bot,
        user_id: int,
        item: Dict[str, Any],
    ) -> bool:
        """Fallback to send media directly using stored file_id."""
        file_id = item.get("file_id")
        media_type = item.get("media_type")
        caption = item.get("caption")

        if not file_id:
            return False

        try:
            if media_type == "photo":
                await bot.send_photo(chat_id=user_id, photo=file_id, caption=caption)
            elif media_type == "video":
                await bot.send_video(chat_id=user_id, video=file_id, caption=caption)
            elif media_type == "document":
                await bot.send_document(chat_id=user_id, document=file_id, caption=caption)
            elif media_type == "audio":
                await bot.send_audio(chat_id=user_id, audio=file_id, caption=caption)
            elif media_type == "animation":
                await bot.send_animation(chat_id=user_id, animation=file_id, caption=caption)
            elif media_type == "text" and caption:
                await bot.send_message(chat_id=user_id, text=caption)
            else:
                return False
            return True
        except Exception as e:
            logger.error("file_id fallback failed for user %d: %s", user_id, e)
            return False
