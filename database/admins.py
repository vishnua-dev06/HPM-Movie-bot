"""Administrators repository managing multiple authorized admin IDs in MongoDB."""

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple
from config import settings
from database.mongodb import Database
from utils.logger import logger


class AdminRepository:
    """Repository managing authorized administrator records in MongoDB."""

    @staticmethod
    def _collection():
        return Database.get_db().admins

    @classmethod
    async def bootstrap_admins(cls, env_admin_ids: List[int]) -> None:
        """Seed initial administrators configured in environment variables into MongoDB."""
        if not env_admin_ids:
            return

        collection = cls._collection()
        now = datetime.now(timezone.utc)

        for idx, admin_id in enumerate(env_admin_ids):
            role = "owner" if idx == 0 else "admin"
            await collection.update_one(
                {"admin_id": admin_id},
                {
                    "$setOnInsert": {
                        "admin_id": admin_id,
                        "added_by": 0,  # 0 indicates system bootstrap
                        "added_at": now,
                        "role": role,
                        "status": "active",
                    }
                },
                upsert=True,
            )
        logger.info("Bootstrapped %d administrator(s) in MongoDB.", len(env_admin_ids))

    @classmethod
    async def is_admin(cls, user_id: int) -> bool:
        """Check if user_id is an authorized administrator (via MongoDB or initial env)."""
        if not user_id:
            return False

        # Fast path check against env
        if user_id in settings.get_initial_admin_ids():
            return True

        # Check database
        try:
            doc = await cls._collection().find_one({"admin_id": user_id, "status": "active"})
            return doc is not None
        except Exception as e:
            logger.error("Error checking admin status for user %d: %s", user_id, e)
            return user_id in settings.get_initial_admin_ids()

    @classmethod
    async def is_owner(cls, user_id: int) -> bool:
        """Check if user_id is the primary owner."""
        if not user_id:
            return False
        if user_id == settings.primary_admin_id:
            return True

        doc = await cls._collection().find_one({"admin_id": user_id, "role": "owner"})
        return doc is not None

    @classmethod
    async def add_admin(
        cls,
        admin_id: int,
        added_by: int,
        role: str = "admin",
    ) -> bool:
        """Add a new administrator to MongoDB."""
        now = datetime.now(timezone.utc)
        existing = await cls._collection().find_one({"admin_id": admin_id})
        if existing:
            if existing.get("status") == "active":
                return False
            # Re-activate if previously deactivated
            await cls._collection().update_one(
                {"admin_id": admin_id},
                {"$set": {"status": "active", "added_by": added_by, "added_at": now}},
            )
            return True

        doc = {
            "admin_id": admin_id,
            "added_by": added_by,
            "added_at": now,
            "role": role,
            "status": "active",
        }
        await cls._collection().insert_one(doc)
        logger.info("Administrator %d added by %d", admin_id, added_by)
        return True

    @classmethod
    async def remove_admin(cls, admin_id: int, requested_by: int) -> Tuple[bool, str]:
        """Remove an administrator from MongoDB, enforcing security guardrails."""
        total_admins = await cls.count_admins()
        if total_admins <= 1:
            return False, "Cannot remove the last remaining administrator."

        # Protect initial owner account from accidental removal by non-owners
        if admin_id == settings.primary_admin_id and requested_by != settings.primary_admin_id:
            return False, "The primary owner account cannot be removed by another administrator."

        existing = await cls._collection().find_one({"admin_id": admin_id})
        if not existing:
            return False, "Administrator ID not found in database."

        if existing.get("role") == "owner" and total_admins > 1:
            # Only allow if another admin exists and requested by owner
            if requested_by != settings.primary_admin_id:
                return False, "Owner role cannot be removed by non-owner."

        res = await cls._collection().delete_one({"admin_id": admin_id})
        if res.deleted_count > 0:
            logger.info("Administrator %d removed by %d", admin_id, requested_by)
            return True, "Administrator successfully removed."
        return False, "Failed to remove administrator."

    @classmethod
    async def get_all_admins(cls) -> List[Dict[str, Any]]:
        """Retrieve all active administrators sorted by role and added date."""
        cursor = cls._collection().find({"status": "active"}).sort([("role", 1), ("added_at", 1)])
        return await cursor.to_list(length=None)

    @classmethod
    async def count_admins(cls) -> int:
        """Count total active administrators."""
        return await cls._collection().count_documents({"status": "active"})
