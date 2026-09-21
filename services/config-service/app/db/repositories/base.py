"""Base repository with common CRUD operations."""

from datetime import datetime, timezone
from typing import Generic, List, Optional, TypeVar

from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorDatabase

T = TypeVar("T")


class BaseRepository(Generic[T]):
    """Base repository class with common CRUD operations."""

    def __init__(self, db: AsyncIOMotorDatabase, collection_name: str):
        self.collection = db[collection_name]

    async def find_by_id(self, id: str) -> Optional[dict]:
        """Find document by ID."""
        if not ObjectId.is_valid(id):
            return None
        return await self.collection.find_one({"_id": ObjectId(id)})

    async def find_one(self, filter: dict) -> Optional[dict]:
        """Find single document by filter."""
        return await self.collection.find_one(filter)

    async def find_many(
        self,
        filter: dict,
        skip: int = 0,
        limit: int = 100,
        sort: Optional[List[tuple]] = None,
    ) -> List[dict]:
        """Find multiple documents with pagination."""
        cursor = self.collection.find(filter).skip(skip).limit(limit)
        if sort:
            cursor = cursor.sort(sort)
        return await cursor.to_list(length=limit)

    async def count(self, filter: dict) -> int:
        """Count documents matching filter."""
        return await self.collection.count_documents(filter)

    async def insert_one(self, document: dict) -> str:
        """Insert single document."""
        document["created_at"] = datetime.now(timezone.utc)
        document["updated_at"] = datetime.now(timezone.utc)
        result = await self.collection.insert_one(document)
        return str(result.inserted_id)

    async def update_one(self, id: str, update: dict) -> bool:
        """Update single document."""
        if not ObjectId.is_valid(id):
            return False
        update["updated_at"] = datetime.now(timezone.utc)
        result = await self.collection.update_one(
            {"_id": ObjectId(id)}, {"$set": update}
        )
        return result.modified_count > 0

    async def delete_one(self, id: str) -> bool:
        """Delete single document."""
        if not ObjectId.is_valid(id):
            return False
        result = await self.collection.delete_one({"_id": ObjectId(id)})
        return result.deleted_count > 0

    @staticmethod
    def serialize_doc(doc: dict) -> dict:
        """Convert MongoDB document to serializable dict."""
        if doc and "_id" in doc:
            doc["id"] = str(doc.pop("_id"))
        return doc
