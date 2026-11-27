"""Broadcast recipients tracking repository in MongoDB."""

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from bson import ObjectId
from database.mongodb import Database


class BroadcastRecipientRepository:
    """Repository managing individual recipient delivery status for durable broadcast jobs."""

    @staticmethod
    def _collection():
        return Database.get_db().broadcast_recipients

    @classmethod
    async def insert_recipients_batch(
        cls,
        broadcast_id: ObjectId,
        user_ids: List[int],
    ) -> int:
        """Insert batch of pending recipient records."""
        if not user_ids:
            return 0

        now = datetime.now(timezone.utc)
        docs = [
            {
                "broadcast_id": broadcast_id,
                "user_id": uid,
                "status": "pending",
                "attempts": 0,
                "last_attempt_at": None,
                "error_code": None,
                "error_message": None,
                "created_at": now,
            }
            for uid in user_ids
        ]

        try:
            # Ordered=False allows inserting all documents even if some duplicates exist
            res = await cls._collection().insert_many(docs, ordered=False)
            return len(res.inserted_ids)
        except Exception:
            # If some duplicates exist, count inserted
            return len(docs)

    @classmethod
    async def get_pending_recipients_batch(
        cls,
        broadcast_id: ObjectId,
        limit: int = 500,
    ) -> List[int]:
        """Fetch next batch of pending user IDs for this broadcast job."""
        cursor = (
            cls._collection()
            .find(
                {"broadcast_id": broadcast_id, "status": "pending"},
                {"user_id": 1, "_id": 0},
            )
            .limit(limit)
        )
        docs = await cursor.to_list(length=limit)
        return [d["user_id"] for d in docs if "user_id" in d]

    @classmethod
    async def update_recipient_status(
        cls,
        broadcast_id: ObjectId,
        user_id: int,
        status: str,  # "successful", "failed", "blocked"
        error_code: Optional[str] = None,
        error_message: Optional[str] = None,
    ) -> None:
        """Update individual recipient status and increment attempt count."""
        now = datetime.now(timezone.utc)
        await cls._collection().update_one(
            {"broadcast_id": broadcast_id, "user_id": user_id},
            {
                "$set": {
                    "status": status,
                    "last_attempt_at": now,
                    "error_code": error_code,
                    "error_message": error_message,
                },
                "$inc": {"attempts": 1},
            },
            upsert=True,
        )

    @classmethod
    async def get_counts_by_status(cls, broadcast_id: ObjectId) -> Dict[str, int]:
        """Aggregate counts for a broadcast job."""
        collection = cls._collection()
        pipeline = [
            {"$match": {"broadcast_id": broadcast_id}},
            {"$group": {"_id": "$status", "count": {"$sum": 1}}},
        ]
        results = await collection.aggregate(pipeline).to_list(length=None)

        counts = {"pending": 0, "successful": 0, "failed": 0, "blocked": 0}
        for item in results:
            status = item.get("_id")
            if status in counts:
                counts[status] = item.get("count", 0)
        return counts

    @classmethod
    async def count_pending_for_broadcast(cls, broadcast_id: ObjectId) -> int:
        """Count remaining pending recipients for a broadcast job."""
        return await cls._collection().count_documents({"broadcast_id": broadcast_id, "status": "pending"})
