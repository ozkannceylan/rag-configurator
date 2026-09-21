"""User service with business logic."""

from motor.motor_asyncio import AsyncIOMotorDatabase

from app.core.audit import AuditLogger
from app.core.exceptions import AlreadyExistsException, NotFoundException
from app.db.repositories.user_repo import UserRepository
from app.schemas.user import UserResponse, UserUpdate


class UserService:
    """Service for user operations."""

    def __init__(self, db: AsyncIOMotorDatabase):
        self.user_repo = UserRepository(db)
        self.audit_logger = AuditLogger(db)

    async def get_by_id(self, user_id: str) -> UserResponse:
        """Get user by ID."""
        user = await self.user_repo.find_by_id(user_id)

        if not user:
            raise NotFoundException("User", user_id)

        user = UserRepository.serialize_doc(user)
        return UserResponse(**user)

    async def update(self, user_id: str, data: UserUpdate) -> UserResponse:
        """Update user."""
        # Check if email is being changed to an existing email
        if data.email:
            existing = await self.user_repo.find_by_email(data.email)
            if existing and str(existing["_id"]) != user_id:
                raise AlreadyExistsException("User", "email", data.email)

        # Update only provided fields
        update_data = data.model_dump(exclude_unset=True)

        if update_data:
            success = await self.user_repo.update_user(user_id, update_data)
            if not success:
                raise NotFoundException("User", user_id)
            await self.audit_logger.log(
                user_id=user_id,
                action="user.update",
                resource_type="user",
                resource_id=user_id,
                details={"fields": sorted(update_data.keys())},
            )

        return await self.get_by_id(user_id)

    async def delete(self, user_id: str) -> bool:
        """Soft delete user (deactivate)."""
        success = await self.user_repo.deactivate_user(user_id)
        if not success:
            raise NotFoundException("User", user_id)
        await self.audit_logger.log(
            user_id=user_id,
            action="user.delete",
            resource_type="user",
            resource_id=user_id,
        )
        return True
