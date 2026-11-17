"""User database operations."""

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from database.mongodb import Database


class UserRepository:
    """Repository for user management in MongoDB."""

    @staticmethod
    def _collection():
        return Database.get_db().users

    @classmethod
    async def upsert_user(
        cls,
        user_id: int,
        username: Optional[str],
        first_name: str,
        last_name: Optional[str] = None,
        is_admin: bool = False,
    ) -> Dict[str, Any]:
        """Create a new user or update an existing user's profile and last_active_at."""
        now = datetime.now(timezone.utc)
        collection = cls._collection()

        update_data = {
            "$set": {
                "username": username,
                "first_name": first_name,
                "last_name": last_name,
                "last_active_at": now,
                "is_admin": is_admin,
            },
            "$setOnInsert": {
                "user_id": user_id,
                "joined_at": now,
                "status": "active",
                "broadcast_eligible": True,
            },
        }

        result = await collection.find_one_and_update(
            {"user_id": user_id},
            update_data,
            upsert=True,
            return_document=True,
        )
        return result

    @classmethod
    async def update_last_active(cls, user_id: int) -> None:
        """Update last active timestamp for a user."""
        now = datetime.now(timezone.utc)
        await cls._collection().update_one(
            {"user_id": user_id},
            {"$set": {"last_active_at": now}},
        )

    @classmethod
    async def set_user_status(cls, user_id: int, status: str) -> None:
        """Update user status (e.g. active, blocked)."""
        broadcast_eligible = (status == "active")
        await cls._collection().update_one(
            {"user_id": user_id},
            {
                "$set": {
                    "status": status,
                    "broadcast_eligible": broadcast_eligible,
                    "updated_at": datetime.now(timezone.utc),
                }
            },
        )

    @classmethod
    async def get_user(cls, user_id: int) -> Optional[Dict[str, Any]]:
        """Retrieve user document by Telegram user ID."""
        return await cls._collection().find_one({"user_id": user_id})

    @classmethod
    async def get_total_users_count(cls) -> int:
        """Count total registered users."""
        return await cls._collection().count_documents({})

    @classmethod
    async def get_active_users_count(cls) -> int:
        """Count active users."""
        return await cls._collection().count_documents({"status": "active"})

    @classmethod
    async def get_blocked_users_count(cls) -> int:
        """Count blocked or inaccessible users."""
        return await cls._collection().count_documents({"status": "blocked"})

    @classmethod
    async def get_today_new_users_count(cls) -> int:
        """Count users registered today (UTC)."""
        now = datetime.now(timezone.utc)
        start_of_day = datetime(now.year, now.month, now.day, tzinfo=timezone.utc)
        return await cls._collection().count_documents({"joined_at": {"$gte": start_of_day}})

    @classmethod
    async def get_recent_users(cls, limit: int = 10) -> List[Dict[str, Any]]:
        """Fetch recently joined users."""
        cursor = cls._collection().find({}).sort("joined_at", -1).limit(limit)
        return await cursor.to_list(length=limit)

    @classmethod
    async def get_all_active_user_ids(cls) -> List[int]:
        """Fetch all user IDs eligible for broadcast."""
        cursor = cls._collection().find(
            {"status": "active", "broadcast_eligible": True},
            {"user_id": 1, "_id": 0},
        )
        users = await cursor.to_list(length=None)
        return [u["user_id"] for u in users]
