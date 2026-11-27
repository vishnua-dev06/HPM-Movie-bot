"""User database operations with scalable batch streaming and registration tracking."""

from datetime import datetime, timezone
from typing import Any, AsyncGenerator, Dict, List, Optional, Tuple
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
        language_code: Optional[str] = None,
        is_admin: bool = False,
        registration_source: str = "start_command",
    ) -> Tuple[Dict[str, Any], bool]:
        """Create a new user or update an existing user's profile and last_active_at.

        Returns:
            Tuple[Dict[str, Any], bool]: (user_document, is_new_user)
        """
        now = datetime.now(timezone.utc)
        collection = cls._collection()

        # Check existence first to reliably detect first-time registrations
        existing = await collection.find_one({"user_id": user_id})
        is_new_user = existing is None

        update_data = {
            "$set": {
                "username": username,
                "first_name": first_name,
                "last_name": last_name,
                "language_code": language_code,
                "last_active_at": now,
                "is_admin": is_admin,
            },
            "$setOnInsert": {
                "user_id": user_id,
                "first_started_at": now,
                "joined_at": now,
                "status": "active",
                "is_blocked": False,
                "broadcast_eligible": True,
                "registration_source": registration_source,
            },
        }

        # If user was previously marked blocked but sends /start, unblock them
        if existing and existing.get("is_blocked"):
            update_data["$set"]["status"] = "active"
            update_data["$set"]["is_blocked"] = False
            update_data["$set"]["broadcast_eligible"] = True

        result = await collection.find_one_and_update(
            {"user_id": user_id},
            update_data,
            upsert=True,
            return_document=True,
        )
        return result, is_new_user

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
        is_blocked = (status == "blocked")
        broadcast_eligible = not is_blocked
        now = datetime.now(timezone.utc)
        await cls._collection().update_one(
            {"user_id": user_id},
            {
                "$set": {
                    "status": status,
                    "is_blocked": is_blocked,
                    "broadcast_eligible": broadcast_eligible,
                    "updated_at": now,
                }
            },
        )

    @classmethod
    async def mark_user_blocked(cls, user_id: int) -> None:
        """Flag user as blocked when Telegram reports permanent forbidden/blocked error."""
        await cls.set_user_status(user_id=user_id, status="blocked")

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
        """Count active users eligible for broadcast."""
        return await cls._collection().count_documents({
            "is_blocked": {"$ne": True},
            "status": "active",
        })

    @classmethod
    async def get_blocked_users_count(cls) -> int:
        """Count blocked or inaccessible users."""
        return await cls._collection().count_documents({
            "$or": [{"status": "blocked"}, {"is_blocked": True}],
        })

    @classmethod
    async def get_today_new_users_count(cls) -> int:
        """Count users registered today (UTC)."""
        now = datetime.now(timezone.utc)
        start_of_day = datetime(now.year, now.month, now.day, tzinfo=timezone.utc)
        return await cls._collection().count_documents({
            "$or": [
                {"first_started_at": {"$gte": start_of_day}},
                {"joined_at": {"$gte": start_of_day}},
            ]
        })

    @classmethod
    async def get_recent_users(cls, limit: int = 10) -> List[Dict[str, Any]]:
        """Fetch recently joined users."""
        cursor = cls._collection().find({}).sort("joined_at", -1).limit(limit)
        return await cursor.to_list(length=limit)

    @classmethod
    async def get_all_active_user_ids(cls) -> List[int]:
        """Fetch all user IDs eligible for broadcast."""
        cursor = cls._collection().find(
            {"is_blocked": {"$ne": True}, "status": "active"},
            {"user_id": 1, "_id": 0},
        )
        users = await cursor.to_list(length=None)
        return [u["user_id"] for u in users if "user_id" in u]

    @classmethod
    async def stream_active_user_ids_in_batches(
        cls,
        batch_size: int = 500,
    ) -> AsyncGenerator[List[int], None]:
        """Stream active user IDs in batches to scale to 100k-300k users without memory overload."""
        cursor = (
            cls._collection()
            .find(
                {"is_blocked": {"$ne": True}, "status": "active"},
                {"user_id": 1, "_id": 0},
            )
            .batch_size(batch_size)
        )

        batch: List[int] = []
        async for doc in cursor:
            if "user_id" in doc:
                batch.append(doc["user_id"])
                if len(batch) >= batch_size:
                    yield batch
                    batch = []

        if batch:
            yield batch
