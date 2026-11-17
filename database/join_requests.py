"""Join request tracking for Private Sub 2 channel."""

from datetime import datetime, timezone
from typing import Optional
from database.mongodb import Database
from utils.logger import logger


class JoinRequestRepository:
    """Repository storing recorded join requests for Sub 2."""

    @staticmethod
    def _collection():
        return Database.get_db().join_requests

    @classmethod
    async def record_join_request(cls, user_id: int, channel_id: int) -> bool:
        """Record or update that a user requested to join a channel."""
        now = datetime.now(timezone.utc)
        try:
            await cls._collection().update_one(
                {"user_id": user_id, "channel_id": channel_id},
                {"$set": {"user_id": user_id, "channel_id": channel_id, "created_at": now}},
                upsert=True,
            )
            logger.info("Recorded join request for user %d in channel %d", user_id, channel_id)
            return True
        except Exception as e:
            logger.error("Error recording join request: %s", e)
            return False

    @classmethod
    async def has_join_request(cls, user_id: int, channel_id: int) -> bool:
        """Check if a join request is recorded for user in channel."""
        doc = await cls._collection().find_one({"user_id": user_id, "channel_id": channel_id})
        return doc is not None

    @classmethod
    async def delete_join_request(cls, user_id: int, channel_id: int) -> bool:
        """Remove join request record (e.g. if revoked or reset)."""
        res = await cls._collection().delete_one({"user_id": user_id, "channel_id": channel_id})
        return res.deleted_count > 0

    @classmethod
    async def count_requests_for_channel(cls, channel_id: int) -> int:
        """Count total join requests recorded for a channel."""
        return await cls._collection().count_documents({"channel_id": channel_id})
