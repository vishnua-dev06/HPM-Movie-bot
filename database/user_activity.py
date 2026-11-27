"""User activity event log repository in MongoDB."""

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from database.mongodb import Database


class UserActivityRepository:
    """Repository storing user activity events."""

    @staticmethod
    def _collection():
        return Database.get_db().user_activity

    @classmethod
    async def log_event(
        cls,
        user_id: int,
        event_type: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Log a user activity event."""
        now = datetime.now(timezone.utc)
        doc = {
            "user_id": user_id,
            "event_type": event_type,
            "metadata": metadata or {},
            "timestamp": now,
        }
        try:
            await cls._collection().insert_one(doc)
        except Exception:
            pass

    @classmethod
    async def get_recent_activity(cls, limit: int = 15) -> List[Dict[str, Any]]:
        """Fetch latest activity records."""
        cursor = cls._collection().find({}).sort("timestamp", -1).limit(limit)
        return await cursor.to_list(length=limit)
