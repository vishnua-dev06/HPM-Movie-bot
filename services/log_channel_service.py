"""User Log Channel integration service."""

from datetime import datetime, timezone
from typing import Optional, Tuple
from aiogram import Bot
from aiogram.types import User
from database.log_channel import LogChannelRepository
from utils.helpers import escape_html
from utils.logger import logger


class LogChannelService:
    """Service handling real-time administrative notifications to the designated Telegram Log Channel."""

    @classmethod
    async def log_new_user_registration(cls, bot: Bot, user: User) -> bool:
        """Send a formatted notification to the Log Channel when a user starts the bot for the first time."""
        try:
            config = await LogChannelRepository.get_config()
            channel_id = config.get("channel_id", 0)
            is_enabled = config.get("is_enabled", False)

            if not is_enabled or not channel_id:
                return False

            now = datetime.now(timezone.utc)
            date_str = now.strftime("%d %B %Y")
            time_str = now.strftime("%I:%M %p UTC")

            user_id = user.id
            username_str = f"@{escape_html(user.username)}" if user.username else "<i>None</i>"
            first_name = escape_html(user.first_name or "Unknown")
            last_name = escape_html(user.last_name or "<i>None</i>")
            lang_code = escape_html(user.language_code or "<i>N/A</i>")
            profile_link = f'<a href="tg://user?id={user_id}">Telegram Profile</a>'

            text = (
                "🆕 <b>NEW USER STARTED THE BOT</b>\n\n"
                f"<b>User ID:</b> <code>{user_id}</code>\n"
                f"<b>Username:</b> {username_str}\n"
                f"<b>First Name:</b> {first_name}\n"
                f"<b>Last Name:</b> {last_name}\n"
                f"<b>Profile:</b> {profile_link}\n"
                f"<b>Registered Date:</b> {date_str}\n"
                f"<b>Registered Time:</b> {time_str}\n"
                f"<b>Language Code:</b> {lang_code}"
            )

            await bot.send_message(
                chat_id=channel_id,
                text=text,
                parse_mode="HTML",
                disable_web_page_preview=True,
            )
            logger.info("Sent new user registration log for user %d to channel %d", user_id, channel_id)
            return True

        except Exception as e:
            # Important Rule: Log Channel failures must NEVER crash user registration or the bot!
            logger.warning("Could not send user registration log to Log Channel (%s): %s", channel_id, e)
            return False

    @classmethod
    async def log_activity_event(cls, bot: Bot, event_title: str, details_text: str) -> bool:
        """Optionally log important administrative and user events if activity logging is enabled."""
        try:
            config = await LogChannelRepository.get_config()
            if not config.get("is_enabled") or not config.get("log_activities"):
                return False

            channel_id = config.get("channel_id")
            if not channel_id:
                return False

            now = datetime.now(timezone.utc).strftime("%I:%M %p UTC")
            text = f"📋 <b>{escape_html(event_title)}</b> [{now}]\n\n{details_text}"

            await bot.send_message(
                chat_id=channel_id,
                text=text,
                parse_mode="HTML",
                disable_web_page_preview=True,
            )
            return True
        except Exception as e:
            logger.debug("Failed sending activity log: %s", e)
            return False

    @classmethod
    async def test_log_channel(cls, bot: Bot, channel_id: int) -> Tuple[bool, str]:
        """Test sending a verification message to ensure the bot has permission to post in the Log Channel."""
        try:
            now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
            test_msg = (
                "✅ <b>LOG CHANNEL VERIFICATION TEST SUCCESSFUL!</b>\n\n"
                f"<b>Bot Status:</b> Connected & Authorized\n"
                f"<b>Channel ID:</b> <code>{channel_id}</code>\n"
                f"<b>Timestamp:</b> {now}\n\n"
                "<i>Malayalam Movie Bot will post new user registration alerts to this channel.</i>"
            )
            await bot.send_message(
                chat_id=channel_id,
                text=test_msg,
                parse_mode="HTML",
            )
            return True, "Verification message successfully delivered to channel."
        except Exception as e:
            logger.error("Log channel verification failed for %d: %s", channel_id, e)
            return False, str(e)
