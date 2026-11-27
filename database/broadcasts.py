"""Broadcast jobs repository managing durable broadcast state in MongoDB."""

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from bson import ObjectId
from database.mongodb import Database


class BroadcastRepository:
    """Repository managing broadcast jobs in MongoDB."""

    @staticmethod
    def _collection():
        return Database.get_db().broadcasts

    @classmethod
    async def create_broadcast_job(
        cls,
        created_by: int,
        total_recipients: int,
        messages: List[Dict[str, Any]],
    ) -> ObjectId:
        """Create a new durable broadcast job record."""
        now = datetime.now(timezone.utc)
        doc = {
            "created_by": created_by,
            "total_recipients": total_recipients,
            "processed": 0,
            "successful": 0,
            "failed": 0,
            "remaining": total_recipients,
            "message_count": len(messages),
            "messages": messages,
            "status": "queued",
            "created_at": now,
            "started_at": None,
            "completed_at": None,
            "duration": None,
            "last_progress_updated_at": now,
        }
        res = await cls._collection().insert_one(doc)
        return res.inserted_id

    @classmethod
    async def get_broadcast_job(cls, broadcast_id: ObjectId | str) -> Optional[Dict[str, Any]]:
        """Fetch broadcast job document."""
        if isinstance(broadcast_id, str):
            broadcast_id = ObjectId(broadcast_id)
        return await cls._collection().find_one({"_id": broadcast_id})

    @classmethod
    async def mark_started(cls, broadcast_id: ObjectId) -> None:
        """Mark broadcast as in_progress."""
        now = datetime.now(timezone.utc)
        await cls._collection().update_one(
            {"_id": broadcast_id},
            {"$set": {"status": "in_progress", "started_at": now, "last_progress_updated_at": now}},
        )

    @classmethod
    async def update_progress(
        cls,
        broadcast_id: ObjectId,
        processed: int,
        successful: int,
        failed: int,
        remaining: int,
    ) -> None:
        """Update live broadcast job metrics."""
        now = datetime.now(timezone.utc)
        await cls._collection().update_one(
            {"_id": broadcast_id},
            {
                "$set": {
                    "processed": processed,
                    "successful": successful,
                    "failed": failed,
                    "remaining": remaining,
                    "last_progress_updated_at": now,
                }
            },
        )

    @classmethod
    async def complete_broadcast_job(
        cls,
        broadcast_id: ObjectId,
        successful: int,
        failed: int,
        total_recipients: int,
        duration_str: str,
    ) -> None:
        """Mark broadcast job completed with final stats."""
        now = datetime.now(timezone.utc)
        await cls._collection().update_one(
            {"_id": broadcast_id},
            {
                "$set": {
                    "status": "completed",
                    "processed": successful + failed,
                    "successful": successful,
                    "failed": failed,
                    "remaining": max(0, total_recipients - (successful + failed)),
                    "completed_at": now,
                    "duration": duration_str,
                }
            },
        )

    @classmethod
    async def get_unfinished_broadcasts(cls) -> List[Dict[str, Any]]:
        """Find any broadcast jobs interrupted by server restart for safe recovery."""
        cursor = cls._collection().find(
            {"status": {"$in": ["queued", "in_progress"]}}
        ).sort("created_at", 1)
        return await cursor.to_list(length=None)

    @classmethod
    async def get_total_broadcasts_count(cls) -> int:
        """Count total completed or active broadcast jobs."""
        return await cls._collection().count_documents({})

    @classmethod
    async def get_recent_broadcasts(cls, limit: int = 5) -> List[Dict[str, Any]]:
        """Retrieve recent broadcast records."""
        cursor = cls._collection().find({}).sort("created_at", -1).limit(limit)
        return await cursor.to_list(length=limit)
