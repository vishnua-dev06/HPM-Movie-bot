"""Log channel settings persistence in MongoDB."""

from datetime import datetime, timezone
from typing import Any, Dict, Optional
from config import settings
from database.mongodb import Database


class LogChannelRepository:
    """Repository storing dynamic User Log Channel settings in MongoDB."""

    @staticmethod
    def _collection():
        return Database.get_db().log_channel_settings

    @classmethod
    async def get_config(cls) -> Dict[str, Any]:
        """Retrieve active log channel settings, falling back to environment defaults."""
        doc = await cls._collection().find_one({"key": "user_log_channel"})
        if not doc:
            return {
                "channel_id": settings.LOG_CHANNEL_ID,
                "is_enabled": settings.LOG_CHANNEL_ID != 0,
                "log_activities": settings.LOG_USER_ACTIVITIES,
            }

        return {
            "channel_id": doc.get("channel_id", settings.LOG_CHANNEL_ID),
            "is_enabled": doc.get("is_enabled", True),
            "log_activities": doc.get("log_activities", settings.LOG_USER_ACTIVITIES),
        }

    @classmethod
    async def set_channel_id(cls, channel_id: int) -> None:
        """Update Log Channel ID dynamically."""
        now = datetime.now(timezone.utc)
        await cls._collection().update_one(
            {"key": "user_log_channel"},
            {
                "$set": {
                    "key": "user_log_channel",
                    "channel_id": channel_id,
                    "is_enabled": True,
                    "updated_at": now,
                }
            },
            upsert=True,
        )

    @classmethod
    async def toggle_enabled(cls, is_enabled: bool) -> None:
        """Enable or disable Log Channel sending."""
        now = datetime.now(timezone.utc)
        await cls._collection().update_one(
            {"key": "user_log_channel"},
            {"$set": {"is_enabled": is_enabled, "updated_at": now}},
            upsert=True,
        )

    @classmethod
    async def toggle_activities(cls, log_activities: bool) -> None:
        """Toggle detailed activity logs in the Log Channel."""
        now = datetime.now(timezone.utc)
        await cls._collection().update_one(
            {"key": "user_log_channel"},
            {"$set": {"log_activities": log_activities, "updated_at": now}},
            upsert=True,
        )
