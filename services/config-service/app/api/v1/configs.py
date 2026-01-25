"""Configuration CRUD endpoints."""

from fastapi import APIRouter, Depends, status, Query
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.db.mongodb import get_db
from app.api.deps import CurrentUser
from app.schemas.config import (
    ConfigCreate,
    ConfigUpdate,
    ConfigResponse,
    ConfigListResponse,
)
from app.schemas.auth import MessageResponse
from app.services.config_service import ConfigService

router = APIRouter(prefix="/configs", tags=["configurations"])


@router.get(
    "/",
    response_model=ConfigListResponse,
    summary="List configurations",
)
async def list_configs(
    current_user: CurrentUser,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncIOMotorDatabase = Depends(get_db),
) -> ConfigListResponse:
    """
    List all configurations for the current user.

    Supports pagination with page and page_size parameters.
    """
    service = ConfigService(db)
    return await service.list(current_user.id, page, page_size)


@router.post(
    "/",
    response_model=ConfigResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create configuration",
)
async def create_config(
    data: ConfigCreate,
    current_user: CurrentUser,
    db: AsyncIOMotorDatabase = Depends(get_db),
) -> ConfigResponse:
    """
    Create a new RAG pipeline configuration.
    """
    service = ConfigService(db)
    return await service.create(data, current_user.id)


@router.get(
    "/{config_id}",
    response_model=ConfigResponse,
    summary="Get configuration",
)
async def get_config(
    config_id: str,
    current_user: CurrentUser,
    db: AsyncIOMotorDatabase = Depends(get_db),
) -> ConfigResponse:
    """
    Get a specific configuration by ID.
    """
    service = ConfigService(db)
    return await service.get_by_id(config_id, current_user.id)


@router.put(
    "/{config_id}",
    response_model=ConfigResponse,
    summary="Update configuration",
)
async def update_config(
    config_id: str,
    data: ConfigUpdate,
    current_user: CurrentUser,
    db: AsyncIOMotorDatabase = Depends(get_db),
) -> ConfigResponse:
    """
    Update an existing configuration.

    Only provided fields will be updated.
    """
    service = ConfigService(db)
    return await service.update(config_id, data, current_user.id)


@router.delete(
    "/{config_id}",
    response_model=MessageResponse,
    summary="Delete configuration",
)
async def delete_config(
    config_id: str,
    current_user: CurrentUser,
    db: AsyncIOMotorDatabase = Depends(get_db),
) -> MessageResponse:
    """
    Delete a configuration.
    """
    service = ConfigService(db)
    await service.delete(config_id, current_user.id)
    return MessageResponse(message="Configuration deleted successfully")


@router.post(
    "/{config_id}/duplicate",
    response_model=ConfigResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Duplicate configuration",
)
async def duplicate_config(
    config_id: str,
    current_user: CurrentUser,
    new_name: str = Query(..., min_length=1, max_length=100),
    db: AsyncIOMotorDatabase = Depends(get_db),
) -> ConfigResponse:
    """
    Create a copy of an existing configuration with a new name.
    """
    service = ConfigService(db)
    return await service.duplicate(config_id, current_user.id, new_name)
