"""Year catalog management in MongoDB."""

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from database.mongodb import Database


class YearRepository:
    """Repository managing release years in MongoDB."""

    @staticmethod
    def _collection():
        return Database.get_db().years

    @classmethod
    async def ensure_year_exists(cls, year: int) -> None:
        """Create year document if it does not already exist."""
        now = datetime.now(timezone.utc)
        await cls._collection().update_one(
            {"year": year},
            {
                "$setOnInsert": {
                    "year": year,
                    "is_enabled": True,
                    "order": year,
                    "created_at": now,
                }
            },
            upsert=True,
        )

    @classmethod
    async def add_year(cls, year: int, order: Optional[int] = None) -> bool:
        """Add a new release year."""
        existing = await cls._collection().find_one({"year": year})
        if existing:
            return False

        now = datetime.now(timezone.utc)
        doc = {
            "year": year,
            "is_enabled": True,
            "order": order if order is not None else year,
            "created_at": now,
        }
        await cls._collection().insert_one(doc)
        return True

    @classmethod
    async def get_all_years(cls, only_enabled: bool = False) -> List[Dict[str, Any]]:
        """Retrieve all years, sorted descending by year."""
        query = {"is_enabled": True} if only_enabled else {}
        cursor = cls._collection().find(query).sort("year", -1)
        return await cursor.to_list(length=None)

    @classmethod
    async def get_years_with_movies(
        cls,
        category: str,
        only_enabled: bool = True,
    ) -> List[int]:
        """Get distinct years that contain at least one movie for the given category."""
        db = Database.get_db()
        # Find distinct years in movies for this category
        distinct_years = await db.movies.distinct("year", {"category": category})
        if not distinct_years:
            return []

        # If only_enabled is True, filter against enabled years in years collection
        if only_enabled:
            enabled_docs = await cls._collection().find(
                {"year": {"$in": distinct_years}, "is_enabled": True},
                {"year": 1, "_id": 0},
            ).to_list(length=None)
            enabled_years = {d["year"] for d in enabled_docs}
            # Also include years that might not have an explicit years entry yet if desired,
            # or auto-ensure them. To be safe, ensure them and filter.
            res = sorted([y for y in distinct_years if y in enabled_years or not enabled_docs], reverse=True)
            return res

        return sorted(distinct_years, reverse=True)

    @classmethod
    async def toggle_year_enabled(cls, year: int, is_enabled: bool) -> bool:
        """Enable or disable a year."""
        res = await cls._collection().update_one(
            {"year": year},
            {"$set": {"is_enabled": is_enabled}},
        )
        return res.modified_count > 0

    @classmethod
    async def rename_year(cls, old_year: int, new_year: int) -> bool:
        """Rename a release year and update associated movies."""
        db = Database.get_db()
        # Update year document
        res = await cls._collection().update_one(
            {"year": old_year},
            {"$set": {"year": new_year, "order": new_year}},
        )
        if res.modified_count > 0:
            # Update all movies with old_year
            await db.movies.update_many(
                {"year": old_year},
                {"$set": {"year": new_year, "updated_at": datetime.now(timezone.utc)}},
            )
            return True
        return False

    @classmethod
    async def delete_year(cls, year: int, cascade_movies: bool = False) -> bool:
        """Delete a year record, optionally deleting all associated movies."""
        db = Database.get_db()
        if cascade_movies:
            # Find all movies for this year
            movies = await db.movies.find({"year": year}, {"_id": 1}).to_list(length=None)
            movie_ids = [m["_id"] for m in movies]
            if movie_ids:
                # Delete messages
                await db.movie_messages.delete_many({"movie_id": {"$in": movie_ids}})
                # Delete movies
                await db.movies.delete_many({"year": year})

        res = await cls._collection().delete_one({"year": year})
        return res.deleted_count > 0

    @classmethod
    async def count_movies_in_year(cls, year: int) -> int:
        """Count total movies existing for a given year."""
        return await Database.get_db().movies.count_documents({"year": year})

    @classmethod
    async def get_total_years_count(cls) -> int:
        """Count total registered years."""
        return await cls._collection().count_documents({})
