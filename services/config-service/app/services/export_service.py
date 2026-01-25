"""Configuration export/import service."""

import yaml
from datetime import datetime
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.core.exceptions import (
    NotFoundException,
    ForbiddenException,
    ValidationException,
)
from app.db.repositories.config_repo import ConfigRepository
from app.services.config_service import ConfigService
from app.schemas.config import ConfigCreate


class ExportService:
    """Service for exporting and importing configurations."""

    def __init__(self, db: AsyncIOMotorDatabase):
        self.config_repo = ConfigRepository(db)
        self.config_service = ConfigService(db)

    async def export_yaml(self, config_id: str, user_id: str) -> str:
        """Export configuration as YAML."""
        config = await self.config_repo.find_by_id(config_id)

        if not config:
            raise NotFoundException("Configuration", config_id)

        if config.get("created_by") != user_id:
            raise ForbiddenException("You don't have access to this configuration")

        # Prepare export data (exclude internal fields)
        export_data = {
            "name": config["name"],
            "description": config.get("description", ""),
            "version": config.get("version", "1.0.0"),
            "data_source": config["data_source"],
            "rbac": config.get("rbac"),
            "models": config["models"],
            "retrieval": config["retrieval"],
            "chunking": config.get("chunking"),
            "agent": config["agent"],
            "prompts": config["prompts"],
        }

        # Add metadata as comments
        metadata = {
            "_metadata": {
                "exported_at": datetime.utcnow().isoformat(),
                "original_id": str(config["_id"]),
                "rag_configurator_version": "1.0.0",
            }
        }

        # Convert to YAML
        yaml_content = yaml.dump(
            {**metadata, **export_data},
            default_flow_style=False,
            allow_unicode=True,
            sort_keys=False,
        )

        return yaml_content

    async def import_yaml(self, yaml_content: str, user_id: str) -> dict:
        """Import configuration from YAML."""
        try:
            data = yaml.safe_load(yaml_content)
        except yaml.YAMLError as e:
            raise ValidationException(f"Invalid YAML format: {str(e)}")

        if not isinstance(data, dict):
            raise ValidationException("YAML must contain a configuration object")

        # Remove metadata if present
        data.pop("_metadata", None)

        # Validate required fields
        required_fields = [
            "name",
            "data_source",
            "models",
            "retrieval",
            "agent",
            "prompts",
        ]
        missing = [f for f in required_fields if f not in data]
        if missing:
            raise ValidationException(f"Missing required fields: {', '.join(missing)}")

        try:
            # Validate against schema
            config_create = ConfigCreate(**data)
        except Exception as e:
            raise ValidationException(f"Invalid configuration format: {str(e)}")

        # Create the configuration
        result = await self.config_service.create(config_create, user_id)
        return result
