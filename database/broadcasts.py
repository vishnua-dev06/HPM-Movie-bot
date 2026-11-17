"""Broadcast history database operations."""

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from bson import ObjectId
from database.mongodb import Database


class BroadcastRepository:
    """Repository managing broadcast logs and metrics."""

    @staticmethod
    def _collection():
        return Database.get_db().broadcasts

    @classmethod
    async def create_broadcast(cls, admin_id: int, total_users: int) -> ObjectId:
        """Create a new broadcast record."""
        now = datetime.now(timezone.utc)
        doc = {
            "admin_id": admin_id,
            "total_users": total_users,
            "success_count": 0,
            "failed_count": 0,
            "blocked_count": 0,
            "status": "in_progress",
            "started_at": now,
            "completed_at": None,
        }
        res = await cls._collection().insert_one(doc)
        return res.inserted_id

    @classmethod
    async def complete_broadcast(
        cls,
        broadcast_id: ObjectId,
        success_count: int,
        failed_count: int,
        blocked_count: int,
    ) -> None:
        """Mark a broadcast as completed with final metrics."""
        now = datetime.now(timezone.utc)
        await cls._collection().update_one(
            {"_id": broadcast_id},
            {
                "$set": {
                    "success_count": success_count,
                    "failed_count": failed_count,
                    "blocked_count": blocked_count,
                    "status": "completed",
                    "completed_at": now,
                }
            },
        )

    @classmethod
    async def get_total_broadcasts_count(cls) -> int:
        """Count total broadcasts executed."""
        return await cls._collection().count_documents({})

    @classmethod
    async def get_recent_broadcasts(cls, limit: int = 5) -> List[Dict[str, Any]]:
        """Retrieve recent broadcast records."""
        cursor = cls._collection().find({}).sort("started_at", -1).limit(limit)
        return await cursor.to_list(length=limit)
