"""Movie media messages database operations."""

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from bson import ObjectId
from database.mongodb import Database


class MovieMessageRepository:
    """Repository managing Telegram media message references for movies."""

    @staticmethod
    def _collection():
        return Database.get_db().movie_messages

    @classmethod
    async def add_movie_messages(
        cls,
        movie_id: str | ObjectId,
        messages: List[Dict[str, Any]],
    ) -> int:
        """Add media message records for a movie."""
        if not messages:
            return 0

        if isinstance(movie_id, str):
            movie_id = ObjectId(movie_id)

        now = datetime.now(timezone.utc)
        docs = []
        for idx, msg in enumerate(messages):
            docs.append({
                "movie_id": movie_id,
                "source_chat_id": msg["source_chat_id"],
                "source_message_id": msg["source_message_id"],
                "media_group_id": msg.get("media_group_id"),
                "order": msg.get("order", idx),
                "media_type": msg.get("media_type", "unknown"),
                "file_id": msg.get("file_id"),
                "file_unique_id": msg.get("file_unique_id"),
                "caption": msg.get("caption"),
                "created_at": now,
            })

        result = await cls._collection().insert_many(docs)
        inserted_count = len(result.inserted_ids)

        # Update total media count on movie document
        from database.movies import MovieRepository
        current_messages = await cls.get_messages_by_movie_id(movie_id)
        await MovieRepository.update_movie_media_count(movie_id, len(current_messages))

        return inserted_count

    @classmethod
    async def get_messages_by_movie_id(
        cls,
        movie_id: str | ObjectId,
    ) -> List[Dict[str, Any]]:
        """Retrieve all media messages for a movie sorted by order."""
        if isinstance(movie_id, str):
            movie_id = ObjectId(movie_id)
        cursor = cls._collection().find({"movie_id": movie_id}).sort("order", 1)
        return await cursor.to_list(length=None)

    @classmethod
    async def delete_messages_by_movie_id(cls, movie_id: str | ObjectId) -> int:
        """Delete all media messages for a given movie."""
        if isinstance(movie_id, str):
            movie_id = ObjectId(movie_id)
        res = await cls._collection().delete_many({"movie_id": movie_id})
        return res.deleted_count

    @classmethod
    async def delete_single_message(
        cls,
        message_doc_id: str | ObjectId,
        movie_id: str | ObjectId,
    ) -> bool:
        """Delete a single media message reference."""
        if isinstance(message_doc_id, str):
            message_doc_id = ObjectId(message_doc_id)
        if isinstance(movie_id, str):
            movie_id = ObjectId(movie_id)

        res = await cls._collection().delete_one({"_id": message_doc_id, "movie_id": movie_id})
        if res.deleted_count > 0:
            remaining = await cls.get_messages_by_movie_id(movie_id)
            from database.movies import MovieRepository
            await MovieRepository.update_movie_media_count(movie_id, len(remaining))
            return True
        return False

    @classmethod
    async def get_total_media_count(cls) -> int:
        """Get total count of all media messages across all movies."""
        return await cls._collection().count_documents({})
