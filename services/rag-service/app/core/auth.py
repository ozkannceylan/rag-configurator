"""Request authentication and ownership helpers for RAG endpoints."""

from __future__ import annotations

from typing import Any, Dict, Optional

from bson import ObjectId
from fastapi import HTTPException, Request, status
from motor.motor_asyncio import AsyncIOMotorDatabase


def get_authenticated_user_id(request: Request) -> str:
    """Read the trusted user identity forwarded by the gateway."""
    user_id = request.headers.get("X-User-ID")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing X-User-ID header",
        )
    return user_id


async def get_config_by_id(
    db: AsyncIOMotorDatabase,
    config_id: str,
) -> Optional[Dict[str, Any]]:
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


def get_config_owner(config: Dict[str, Any]) -> Optional[str]:
    """Return the config owner field used by the current document."""
    return config.get("created_by") or config.get("user_id")


async def require_config_access(
    db: AsyncIOMotorDatabase,
    config_id: str,
    user_id: str,
) -> Dict[str, Any]:
    """Require that the user owns the target configuration."""
    config = await get_config_by_id(db, config_id)
    if not config:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Configuration '{config_id}' not found",
        )

    owner_id = get_config_owner(config)
    if owner_id != user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have access to this configuration",
        )

    return config


async def require_conversation_access(
    db: AsyncIOMotorDatabase,
    conversation_id: str,
    user_id: str,
) -> Dict[str, Any]:
    """Require that the user owns the target conversation."""
    conversation = await db["conversations"].find_one({"_id": conversation_id})
    if not conversation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Conversation '{conversation_id}' not found",
        )

    conversation_owner = conversation.get("user_id")
    if conversation_owner and conversation_owner != user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have access to this conversation",
        )

    config_id = conversation.get("config_id")
    if config_id:
        await require_config_access(db, str(config_id), user_id)

    return conversation
