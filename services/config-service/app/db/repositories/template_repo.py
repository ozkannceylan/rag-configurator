"""Template repository for database operations."""

from typing import List, Optional

from motor.motor_asyncio import AsyncIOMotorDatabase

from app.db.repositories.base import BaseRepository


class TemplateRepository(BaseRepository):
    """Repository for config template operations."""

    def __init__(self, db: AsyncIOMotorDatabase):
        super().__init__(db, "templates")

    async def find_all_templates(
        self,
        skip: int = 0,
        limit: int = 20,
        category: Optional[str] = None,
        search: Optional[str] = None,
    ) -> List[dict]:
        """Find all templates with optional filters."""
        filter_query: dict = {}

        if category:
            filter_query["category"] = category

        if search:
            filter_query["$or"] = [
                {"name": {"$regex": search, "$options": "i"}},
                {"description": {"$regex": search, "$options": "i"}},
            ]

        return await self.find_many(
            filter=filter_query,
            skip=skip,
            limit=limit,
            sort=[("usage_count", -1), ("created_at", -1)],
        )

    async def count_templates(
        self,
        category: Optional[str] = None,
        search: Optional[str] = None,
    ) -> int:
        """Count templates matching filters."""
        filter_query: dict = {}

        if category:
            filter_query["category"] = category

        if search:
            filter_query["$or"] = [
                {"name": {"$regex": search, "$options": "i"}},
                {"description": {"$regex": search, "$options": "i"}},
            ]

        return await self.count(filter_query)

    async def create_template(self, template_data: dict) -> str:
        """Create a new template."""
        return await self.insert_one(template_data)

    async def increment_usage(self, template_id: str) -> bool:
        """Increment the usage_count for a template."""
        from bson import ObjectId

        if not ObjectId.is_valid(template_id):
            return False
        result = await self.collection.update_one(
            {"_id": ObjectId(template_id)},
            {"$inc": {"usage_count": 1}},
        )
        return result.modified_count > 0

    async def is_owner(self, template_id: str, user_id: str) -> bool:
        """Check if user owns the template."""
        template = await self.find_by_id(template_id)
        return template is not None and template.get("created_by") == user_id
