"""Activity logging repository in MongoDB."""

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from database.mongodb import Database


class ActivityLogRepository:
    """Repository managing audit and activity logs."""

    @staticmethod
    def _collection():
        return Database.get_db().activity_logs

    @classmethod
    async def log_activity(
        cls,
        user_id: int,
        action: str,
        details: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Insert an activity log record."""
        now = datetime.now(timezone.utc)
        doc = {
            "user_id": user_id,
            "action": action,
            "details": details or {},
            "created_at": now,
        }
        try:
            await cls._collection().insert_one(doc)
        except Exception:
            pass  # Logging should not crash main operation

    @classmethod
    async def get_recent_activity(cls, limit: int = 15) -> List[Dict[str, Any]]:
        """Retrieve latest activity logs."""
        cursor = cls._collection().find({}).sort("created_at", -1).limit(limit)
        return await cursor.to_list(length=limit)
