"""Movie repository for database operations."""

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from bson import ObjectId
from database.mongodb import Database


class MovieRepository:
    """Repository managing movies catalog in MongoDB."""

    @staticmethod
    def _collection():
        return Database.get_db().movies

    @classmethod
    async def create_movie(
        cls,
        title: str,
        category: str,
        year: int,
        total_media: int = 0,
    ) -> ObjectId:
        """Create a new movie document and return its ObjectId."""
        now = datetime.now(timezone.utc)
        doc = {
            "title": title.strip(),
            "category": category,
            "year": year,
            "total_media": total_media,
            "created_at": now,
            "updated_at": now,
        }
        result = await cls._collection().insert_one(doc)
        return result.inserted_id

    @classmethod
    async def get_movie_by_id(cls, movie_id: str | ObjectId) -> Optional[Dict[str, Any]]:
        """Find a movie by its ObjectId string or ObjectId."""
        if isinstance(movie_id, str):
            try:
                movie_id = ObjectId(movie_id)
            except Exception:
                return None
        return await cls._collection().find_one({"_id": movie_id})

    @classmethod
    async def get_movies_by_category_and_year(
        cls,
        category: str,
        year: int,
        skip: int = 0,
        limit: int = 10,
    ) -> List[Dict[str, Any]]:
        """Retrieve paginated movies for a specific category and year."""
        cursor = (
            cls._collection()
            .find({"category": category, "year": year})
            .sort("title", 1)
            .skip(skip)
            .limit(limit)
        )
        return await cursor.to_list(length=limit)

    @classmethod
    async def get_movies_count_by_category_and_year(
        cls,
        category: str,
        year: int,
    ) -> int:
        """Count total movies for a specific category and year."""
        return await cls._collection().count_documents({"category": category, "year": year})

    @classmethod
    async def get_all_movies(
        cls,
        skip: int = 0,
        limit: int = 10,
        category: Optional[str] = None,
        year: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        """Retrieve paginated movies with optional filters."""
        query: Dict[str, Any] = {}
        if category:
            query["category"] = category
        if year:
            query["year"] = year

        cursor = (
            cls._collection()
            .find(query)
            .sort("created_at", -1)
            .skip(skip)
            .limit(limit)
        )
        return await cursor.to_list(length=limit)

    @classmethod
    async def get_total_movies_count(cls) -> int:
        """Count total movies across all categories."""
        return await cls._collection().count_documents({})

    @classmethod
    async def get_movies_count_by_category(cls, category: str) -> int:
        """Count total movies in a specific category."""
        return await cls._collection().count_documents({"category": category})

    @classmethod
    async def update_movie_title(cls, movie_id: str | ObjectId, title: str) -> bool:
        """Update movie title."""
        if isinstance(movie_id, str):
            movie_id = ObjectId(movie_id)
        res = await cls._collection().update_one(
            {"_id": movie_id},
            {
                "$set": {
                    "title": title.strip(),
                    "updated_at": datetime.now(timezone.utc),
                }
            },
        )
        return res.modified_count > 0

    @classmethod
    async def update_movie_category(cls, movie_id: str | ObjectId, category: str) -> bool:
        """Update movie category."""
        if isinstance(movie_id, str):
            movie_id = ObjectId(movie_id)
        res = await cls._collection().update_one(
            {"_id": movie_id},
            {
                "$set": {
                    "category": category,
                    "updated_at": datetime.now(timezone.utc),
                }
            },
        )
        return res.modified_count > 0

    @classmethod
    async def update_movie_year(cls, movie_id: str | ObjectId, year: int) -> bool:
        """Update movie release year."""
        if isinstance(movie_id, str):
            movie_id = ObjectId(movie_id)
        res = await cls._collection().update_one(
            {"_id": movie_id},
            {
                "$set": {
                    "year": year,
                    "updated_at": datetime.now(timezone.utc),
                }
            },
        )
        return res.modified_count > 0

    @classmethod
    async def update_movie_media_count(cls, movie_id: str | ObjectId, count: int) -> bool:
        """Update total media message count for movie."""
        if isinstance(movie_id, str):
            movie_id = ObjectId(movie_id)
        res = await cls._collection().update_one(
            {"_id": movie_id},
            {
                "$set": {
                    "total_media": count,
                    "updated_at": datetime.now(timezone.utc),
                }
            },
        )
        return res.modified_count > 0

    @classmethod
    async def delete_movie(cls, movie_id: str | ObjectId) -> bool:
        """Delete a movie and cascade delete its media messages."""
        if isinstance(movie_id, str):
            movie_id = ObjectId(movie_id)
        # Delete movie messages
        await Database.get_db().movie_messages.delete_many({"movie_id": movie_id})
        # Delete movie
        res = await cls._collection().delete_one({"_id": movie_id})
        return res.deleted_count > 0
