"""Test fixtures and mock in-memory MongoDB environment."""

import asyncio
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
import pytest
from bson import ObjectId
from config import settings
from database.mongodb import Database


class FakeCursor:
    """Mock asynchronous MongoDB cursor."""

    def __init__(self, docs: List[Dict[str, Any]]):
        self.docs = list(docs)

    def sort(self, key_or_list, direction=1):
        if isinstance(key_or_list, list):
            for k, d in reversed(key_or_list):
                reverse = (d == -1)
                self.docs.sort(key=lambda x: x.get(k, 0), reverse=reverse)
        else:
            reverse = (direction == -1)
            self.docs.sort(key=lambda x: x.get(key_or_list, 0), reverse=reverse)
        return self

    def skip(self, count: int):
        self.docs = self.docs[count:]
        return self

    def limit(self, count: int):
        self.docs = self.docs[:count]
        return self

    async def to_list(self, length: Optional[int] = None):
        if length is not None:
            return self.docs[:length]
        return self.docs


class FakeCollection:
    """In-memory mock MongoDB collection."""

    def __init__(self, name: str):
        self.name = name
        self.documents: Dict[str, Dict[str, Any]] = {}

    def _matches(self, doc: Dict[str, Any], query: Dict[str, Any]) -> bool:
        for k, v in query.items():
            if k == "$in" or (isinstance(v, dict) and "$in" in v):
                in_list = v["$in"] if isinstance(v, dict) else v
                if doc.get(k) not in in_list:
                    return False
            elif isinstance(v, dict) and "$gte" in v:
                val = doc.get(k)
                if val is None or val < v["$gte"]:
                    return False
            elif doc.get(k) != v:
                return False
        return True

    async def create_index(self, *args, **kwargs):
        return "index_created"

    async def count_documents(self, query: Dict[str, Any]) -> int:
        return sum(1 for d in self.documents.values() if self._matches(d, query))

    async def find_one(self, query: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        for d in self.documents.values():
            if self._matches(d, query):
                return dict(d)
        return None

    def find(self, query: Dict[str, Any], projection: Optional[Dict[str, Any]] = None) -> FakeCursor:
        matched = [dict(d) for d in self.documents.values() if self._matches(d, query)]
        if projection:
            filtered = []
            for d in matched:
                item = {}
                for k, v in projection.items():
                    if v and k in d:
                        item[k] = d[k]
                filtered.append(item)
            return FakeCursor(filtered)
        return FakeCursor(matched)

    async def distinct(self, key: str, query: Optional[Dict[str, Any]] = None) -> List[Any]:
        query = query or {}
        matched = [d[key] for d in self.documents.values() if self._matches(d, query) and key in d]
        return list(set(matched))

    async def insert_one(self, doc: Dict[str, Any]):
        class InsertResult:
            def __init__(self, ins_id):
                self.inserted_id = ins_id

        doc_copy = dict(doc)
        if "_id" not in doc_copy:
            doc_copy["_id"] = ObjectId()
        key = str(doc_copy["_id"])
        self.documents[key] = doc_copy
        return InsertResult(doc_copy["_id"])

    async def insert_many(self, docs: List[Dict[str, Any]]):
        class InsertManyResult:
            def __init__(self, ids):
                self.inserted_ids = ids

        inserted_ids = []
        for d in docs:
            doc_copy = dict(d)
            if "_id" not in doc_copy:
                doc_copy["_id"] = ObjectId()
            self.documents[str(doc_copy["_id"])] = doc_copy
            inserted_ids.append(doc_copy["_id"])
        return InsertManyResult(inserted_ids)

    async def update_one(self, query: Dict[str, Any], update: Dict[str, Any], upsert: bool = False):
        class UpdateResult:
            def __init__(self, mod_count, upserted_id=None):
                self.modified_count = mod_count
                self.upserted_id = upserted_id

        existing = await self.find_one(query)
        if existing:
            key = str(existing["_id"])
            target = self.documents[key]
            if "$set" in update:
                target.update(update["$set"])
            return UpdateResult(1)
        elif upsert:
            new_doc = dict(query)
            if "$set" in update:
                new_doc.update(update["$set"])
            if "$setOnInsert" in update:
                new_doc.update(update["$setOnInsert"])
            res = await self.insert_one(new_doc)
            return UpdateResult(1, res.inserted_id)
        return UpdateResult(0)

    async def update_many(self, query: Dict[str, Any], update: Dict[str, Any]):
        class UpdateManyResult:
            def __init__(self, mod_count):
                self.modified_count = mod_count

        count = 0
        for key, d in list(self.documents.items()):
            if self._matches(d, query):
                if "$set" in update:
                    d.update(update["$set"])
                count += 1
        return UpdateManyResult(count)

    async def find_one_and_update(self, query: Dict[str, Any], update: Dict[str, Any], upsert: bool = False, **kwargs):
        existing = await self.find_one(query)
        if existing:
            key = str(existing["_id"])
            target = self.documents[key]
            if "$set" in update:
                target.update(update["$set"])
            return dict(target)
        elif upsert:
            new_doc = dict(query)
            if "$set" in update:
                new_doc.update(update["$set"])
            if "$setOnInsert" in update:
                new_doc.update(update["$setOnInsert"])
            await self.insert_one(new_doc)
            return dict(new_doc)
        return None

    async def delete_one(self, query: Dict[str, Any]):
        class DeleteResult:
            def __init__(self, del_count):
                self.deleted_count = del_count

        for key, d in list(self.documents.items()):
            if self._matches(d, query):
                del self.documents[key]
                return DeleteResult(1)
        return DeleteResult(0)

    async def delete_many(self, query: Dict[str, Any]):
        class DeleteManyResult:
            def __init__(self, del_count):
                self.deleted_count = del_count

        count = 0
        for key, d in list(self.documents.items()):
            if self._matches(d, query):
                del self.documents[key]
                count += 1
        return DeleteManyResult(count)


class FakeDatabase:
    """Fake Async MongoDB database container."""

    def __init__(self):
        self._collections: Dict[str, FakeCollection] = {}

    def __getitem__(self, name: str) -> FakeCollection:
        if name not in self._collections:
            self._collections[name] = FakeCollection(name)
        return self._collections[name]

    def __getattr__(self, name: str) -> FakeCollection:
        return self[name]


@pytest.fixture(autouse=True)
def setup_fake_db():
    """Configure in-memory database and test settings for each test."""
    fake_db = FakeDatabase()
    Database.db = fake_db  # type: ignore

    # Set predictable settings for tests
    settings.BOT_TOKEN = "123456789:TEST_MOCK_TOKEN_ABCDEFGHIJKLMN"
    settings.ADMIN_ID = 999999999
    settings.SUB1_CHANNEL_ID = -1001111111111
    settings.SUB1_INVITE_URL = "https://t.me/test_sub1"

    yield fake_db
    Database.db = None
