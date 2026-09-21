"""Configuration repository for database operations."""

from typing import List, Optional

from motor.motor_asyncio import AsyncIOMotorDatabase

from app.db.repositories.base import BaseRepository


class ConfigRepository(BaseRepository):
    """Repository for RAG pipeline configuration operations."""

    def __init__(self, db: AsyncIOMotorDatabase):
        super().__init__(db, "configs")

    async def find_by_user(
        self,
        user_id: str,
        skip: int = 0,
        limit: int = 100,
    ) -> List[dict]:
        """Find all configurations for a user."""
        return await self.find_many(
            filter={"created_by": user_id},
            skip=skip,
            limit=limit,
            sort=[("created_at", -1)],
        )

    async def count_by_user(self, user_id: str) -> int:
        """Count configurations for a user."""
        return await self.count({"created_by": user_id})

    async def find_by_name(self, user_id: str, name: str) -> Optional[dict]:
        """Find configuration by name for a user."""
        return await self.find_one(
            {
                "created_by": user_id,
                "name": name,
            }
        )

    async def create_config(self, config_data: dict) -> str:
        """Create a new configuration."""
        return await self.insert_one(config_data)

    async def update_config(self, config_id: str, update_data: dict) -> bool:
        """Update configuration."""
        return await self.update_one(config_id, update_data)

    async def is_owner(self, config_id: str, user_id: str) -> bool:
        """Check if user owns the configuration."""
        config = await self.find_by_id(config_id)
        return config is not None and config.get("created_by") == user_id
