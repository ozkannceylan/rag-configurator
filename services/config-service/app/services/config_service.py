"""Configuration service with business logic."""

from motor.motor_asyncio import AsyncIOMotorDatabase

from rag_config_common.models.enums import IngestionStatus
from rag_config_common.models.config import RBACConfig, ChunkingConfig

from app.core.exceptions import (
    NotFoundException,
    AlreadyExistsException,
    ForbiddenException,
)
from app.db.repositories.config_repo import ConfigRepository
from app.schemas.config import (
    ConfigCreate,
    ConfigUpdate,
    ConfigResponse,
    ConfigSummary,
    ConfigListResponse,
)


class ConfigService:
    """Service for configuration operations."""

    def __init__(self, db: AsyncIOMotorDatabase):
        self.config_repo = ConfigRepository(db)

    async def create(self, data: ConfigCreate, user_id: str) -> ConfigResponse:
        """Create a new configuration."""
        # Check for duplicate name
        existing = await self.config_repo.find_by_name(user_id, data.name)
        if existing:
            raise AlreadyExistsException("Configuration", "name", data.name)

        # Prepare config document
        config_data = data.model_dump()
        config_data["created_by"] = user_id
        config_data["version"] = "1.0.0"
        config_data["status"] = IngestionStatus.PENDING.value
        config_data["api_endpoint"] = None
        config_data["stats"] = None

        # Set defaults for optional fields
        if config_data.get("rbac") is None:
            config_data["rbac"] = RBACConfig().model_dump()
        if config_data.get("chunking") is None:
            config_data["chunking"] = ChunkingConfig().model_dump()

        # Create config
        config_id = await self.config_repo.create_config(config_data)

        # Fetch and return created config
        return await self.get_by_id(config_id, user_id)

    async def get_by_id(self, config_id: str, user_id: str) -> ConfigResponse:
        """Get configuration by ID."""
        config = await self.config_repo.find_by_id(config_id)

        if not config:
            raise NotFoundException("Configuration", config_id)

        if config.get("created_by") != user_id:
            raise ForbiddenException("You don't have access to this configuration")

        config = ConfigRepository.serialize_doc(config)
        return ConfigResponse(**config)

    async def list(
        self,
        user_id: str,
        page: int = 1,
        page_size: int = 20,
    ) -> ConfigListResponse:
        """List configurations for a user."""
        skip = (page - 1) * page_size

        configs = await self.config_repo.find_by_user(user_id, skip, page_size)
        total = await self.config_repo.count_by_user(user_id)

        items = [
            ConfigSummary(**ConfigRepository.serialize_doc(c)) for c in configs
        ]

        return ConfigListResponse(
            items=items,
            total=total,
            page=page,
            page_size=page_size,
        )

    async def update(
        self,
        config_id: str,
        data: ConfigUpdate,
        user_id: str,
    ) -> ConfigResponse:
        """Update configuration."""
        # Verify ownership
        if not await self.config_repo.is_owner(config_id, user_id):
            config = await self.config_repo.find_by_id(config_id)
            if not config:
                raise NotFoundException("Configuration", config_id)
            raise ForbiddenException("You don't have access to this configuration")

        # Check for duplicate name if name is being changed
        if data.name:
            existing = await self.config_repo.find_by_name(user_id, data.name)
            if existing and str(existing["_id"]) != config_id:
                raise AlreadyExistsException("Configuration", "name", data.name)

        # Update only provided fields
        update_data = data.model_dump(exclude_unset=True)

        if update_data:
            await self.config_repo.update_config(config_id, update_data)

        return await self.get_by_id(config_id, user_id)

    async def delete(self, config_id: str, user_id: str) -> bool:
        """Delete configuration."""
        if not await self.config_repo.is_owner(config_id, user_id):
            config = await self.config_repo.find_by_id(config_id)
            if not config:
                raise NotFoundException("Configuration", config_id)
            raise ForbiddenException("You don't have access to this configuration")

        return await self.config_repo.delete_one(config_id)

    async def duplicate(
        self, config_id: str, user_id: str, new_name: str
    ) -> ConfigResponse:
        """Duplicate a configuration."""
        original = await self.config_repo.find_by_id(config_id)

        if not original:
            raise NotFoundException("Configuration", config_id)

        if original.get("created_by") != user_id:
            raise ForbiddenException("You don't have access to this configuration")

        # Check for duplicate name
        existing = await self.config_repo.find_by_name(user_id, new_name)
        if existing:
            raise AlreadyExistsException("Configuration", "name", new_name)

        # Create copy
        new_config = original.copy()
        del new_config["_id"]
        new_config["name"] = new_name
        new_config["status"] = IngestionStatus.PENDING.value
        new_config["api_endpoint"] = None
        new_config["stats"] = None

        config_id = await self.config_repo.create_config(new_config)
        return await self.get_by_id(config_id, user_id)
