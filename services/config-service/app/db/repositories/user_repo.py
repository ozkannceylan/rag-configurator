"""User repository for database operations."""

from typing import Optional
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.db.repositories.base import BaseRepository


class UserRepository(BaseRepository):
    """Repository for user operations."""

    def __init__(self, db: AsyncIOMotorDatabase):
        super().__init__(db, "users")

    async def find_by_email(self, email: str) -> Optional[dict]:
        """Find user by email address."""
        return await self.find_one({"email": email.lower()})

    async def create_user(self, user_data: dict) -> str:
        """Create a new user."""
        user_data["email"] = user_data["email"].lower()
        user_data["is_active"] = True
        return await self.insert_one(user_data)

    async def update_user(self, user_id: str, update_data: dict) -> bool:
        """Update user data."""
        if "email" in update_data:
            update_data["email"] = update_data["email"].lower()
        return await self.update_one(user_id, update_data)

    async def deactivate_user(self, user_id: str) -> bool:
        """Soft delete user by deactivating."""
        return await self.update_one(user_id, {"is_active": False})
