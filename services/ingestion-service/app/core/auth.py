"""Request authentication and ownership helpers for ingestion endpoints."""

from __future__ import annotations

from typing import Any

from bson import ObjectId
from fastapi import HTTPException, status
from motor.motor_asyncio import AsyncIOMotorDatabase
from rag_config_common.auth.middleware import get_authenticated_user_id

# get_authenticated_user_id is re-exported from rag_config_common so API
# modules import every auth helper from this one local path. It is unused
# inside this module, so __all__ is what marks it public.
__all__ = [
    "get_authenticated_user_id",
    "get_config_by_id",
    "get_config_owner",
    "require_config_access",
]


async def get_config_by_id(
    db: AsyncIOMotorDatabase,
    config_id: str,
) -> dict[str, Any] | None:
    """Load a configuration by ObjectId, string _id, or id field."""
    configs = db["configs"]

    try:
        config = await configs.find_one({"_id": ObjectId(config_id)})
        if config:
            config["_id"] = str(config["_id"])
            return config
    except Exception:
        pass

    config = await configs.find_one({"_id": config_id})
    if config:
        config["_id"] = str(config["_id"])
        return config

    config = await configs.find_one({"id": config_id})
    if config:
        config["_id"] = str(config["_id"])
        return config

    return None


def get_config_owner(config: dict[str, Any]) -> str | None:
    """Return the config owner field used by the current document."""
    return config.get("created_by") or config.get("user_id")


async def require_config_access(
    db: AsyncIOMotorDatabase,
    config_id: str,
    user_id: str,
) -> dict[str, Any]:
    """Require that the user owns the target configuration."""
    config = await get_config_by_id(db, config_id)
    if not config:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Configuration not found: {config_id}",
        )

    owner_id = get_config_owner(config)
    if owner_id != user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have access to this configuration",
        )

    return config
