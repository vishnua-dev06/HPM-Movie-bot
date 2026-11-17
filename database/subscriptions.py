"""Subscription configurations repository for Sub 2."""

from datetime import datetime, timezone
from typing import Any, Dict, Optional
from database.mongodb import Database


class SubscriptionRepository:
    """Repository managing dynamic Sub 2 settings."""

    @staticmethod
    def _collection():
        return Database.get_db().subscriptions

    @classmethod
    async def get_sub2(cls) -> Optional[Dict[str, Any]]:
        """Retrieve dynamic Sub 2 configuration."""
        return await cls._collection().find_one({"slot": "sub2"})

    @classmethod
    async def set_sub2(
        cls,
        channel_id: int,
        channel_type: str,  # "public" or "private_request"
        invite_url: str,
        channel_title: Optional[str] = None,
        is_enabled: bool = True,
    ) -> None:
        """Upsert Sub 2 configuration."""
        now = datetime.now(timezone.utc)
        doc = {
            "slot": "sub2",
            "channel_id": channel_id,
            "channel_type": channel_type,
            "invite_url": invite_url.strip(),
            "channel_title": channel_title,
            "is_enabled": is_enabled,
            "updated_at": now,
        }
        await cls._collection().update_one(
            {"slot": "sub2"},
            {"$set": doc},
            upsert=True,
        )

    @classmethod
    async def toggle_sub2_enabled(cls, is_enabled: bool) -> bool:
        """Enable or disable Sub 2 requirement."""
        res = await cls._collection().update_one(
            {"slot": "sub2"},
            {"$set": {"is_enabled": is_enabled, "updated_at": datetime.now(timezone.utc)}},
        )
        return res.modified_count > 0

    @classmethod
    async def update_sub2_url(cls, invite_url: str) -> bool:
        """Update Sub 2 invite URL."""
        res = await cls._collection().update_one(
            {"slot": "sub2"},
            {"$set": {"invite_url": invite_url.strip(), "updated_at": datetime.now(timezone.utc)}},
        )
        return res.modified_count > 0

    @classmethod
    async def update_sub2_type(cls, channel_type: str) -> bool:
        """Update Sub 2 channel type ('public' or 'private_request')."""
        res = await cls._collection().update_one(
            {"slot": "sub2"},
            {"$set": {"channel_type": channel_type, "updated_at": datetime.now(timezone.utc)}},
        )
        return res.modified_count > 0

    @classmethod
    async def remove_sub2(cls) -> bool:
        """Remove Sub 2 configuration completely."""
        res = await cls._collection().delete_one({"slot": "sub2"})
        return res.deleted_count > 0
