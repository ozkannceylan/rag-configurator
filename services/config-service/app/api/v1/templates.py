"""Template marketplace endpoints."""

from datetime import datetime, timezone
from typing import Optional, List

from fastapi import APIRouter, Depends, status, Query
from motor.motor_asyncio import AsyncIOMotorDatabase
from pydantic import BaseModel, Field

from app.db.mongodb import get_db
from app.api.deps import CurrentUser
from app.core.exceptions import NotFoundException, ForbiddenException
from app.db.repositories.template_repo import TemplateRepository
from app.db.repositories.config_repo import ConfigRepository

router = APIRouter(prefix="/templates", tags=["templates"])


# ==================== Schemas ====================


class TemplateCreate(BaseModel):
    """Request to create a template from an existing config."""

    config_id: str = Field(..., description="Source config ID to create template from")
    name: str = Field(..., min_length=1, max_length=100)
    description: str = Field(default="")
    category: str = Field(default="general")
    tags: List[str] = Field(default_factory=list)


class TemplateResponse(BaseModel):
    """Template response."""

    id: str
    name: str
    description: str
    category: str
    tags: List[str]
    config_snapshot: dict
    created_by: str
    created_at: datetime
    updated_at: datetime
    usage_count: int


class TemplateSummary(BaseModel):
    """Template summary for list views."""

    id: str
    name: str
    description: str
    category: str
    tags: List[str]
    created_by: str
    created_at: datetime
    usage_count: int


class TemplateListResponse(BaseModel):
    """Paginated template list response."""

    items: List[TemplateSummary]
    total: int
    page: int
    page_size: int


# ==================== Endpoints ====================


@router.get(
    "/",
    response_model=TemplateListResponse,
    summary="List templates",
)
async def list_templates(
    current_user: CurrentUser,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    category: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    db: AsyncIOMotorDatabase = Depends(get_db),
) -> TemplateListResponse:
    """List all available templates with optional category filter and search."""
    repo = TemplateRepository(db)
    skip = (page - 1) * page_size

    templates = await repo.find_all_templates(
        skip=skip,
        limit=page_size,
        category=category,
        search=search,
    )
    total = await repo.count_templates(category=category, search=search)

    items = []
    for t in templates:
        t = TemplateRepository.serialize_doc(t)
        items.append(
            TemplateSummary(
                id=t["id"],
                name=t["name"],
                description=t.get("description", ""),
                category=t.get("category", "general"),
                tags=t.get("tags", []),
                created_by=t.get("created_by", ""),
                created_at=t.get("created_at", datetime.now(timezone.utc)),
                usage_count=t.get("usage_count", 0),
            )
        )

    return TemplateListResponse(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get(
    "/{template_id}",
    response_model=TemplateResponse,
    summary="Get template details",
)
async def get_template(
    template_id: str,
    current_user: CurrentUser,
    db: AsyncIOMotorDatabase = Depends(get_db),
) -> TemplateResponse:
    """Get a specific template by ID."""
    repo = TemplateRepository(db)
    template = await repo.find_by_id(template_id)

    if not template:
        raise NotFoundException("Template", template_id)

    template = TemplateRepository.serialize_doc(template)
    return TemplateResponse(**template)


@router.post(
    "/",
    response_model=TemplateResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create template from config",
)
async def create_template(
    data: TemplateCreate,
    current_user: CurrentUser,
    db: AsyncIOMotorDatabase = Depends(get_db),
) -> TemplateResponse:
    """Create a new template from an existing configuration."""
    config_repo = ConfigRepository(db)
    template_repo = TemplateRepository(db)

    # Fetch the source config
    config = await config_repo.find_by_id(data.config_id)
    if not config:
        raise NotFoundException("Configuration", data.config_id)

    if config.get("created_by") != current_user.id:
        raise ForbiddenException("You don't have access to this configuration")

    # Create a snapshot of the config (strip metadata)
    config_snapshot = {
        k: v
        for k, v in config.items()
        if k
        not in (
            "_id",
            "id",
            "created_by",
            "created_at",
            "updated_at",
            "status",
            "api_endpoint",
            "stats",
        )
    }

    template_data = {
        "name": data.name,
        "description": data.description,
        "category": data.category,
        "tags": data.tags,
        "config_snapshot": config_snapshot,
        "created_by": current_user.id,
        "usage_count": 0,
    }

    template_id = await template_repo.create_template(template_data)

    # Fetch and return
    template = await template_repo.find_by_id(template_id)
    template = TemplateRepository.serialize_doc(template)
    return TemplateResponse(**template)


@router.post(
    "/{template_id}/clone",
    status_code=status.HTTP_201_CREATED,
    summary="Clone template as new config",
)
async def clone_template(
    template_id: str,
    current_user: CurrentUser,
    new_name: str = Query(..., min_length=1, max_length=100),
    db: AsyncIOMotorDatabase = Depends(get_db),
) -> dict:
    """Clone a template as a new configuration for the current user."""
    template_repo = TemplateRepository(db)
    config_repo = ConfigRepository(db)

    template = await template_repo.find_by_id(template_id)
    if not template:
        raise NotFoundException("Template", template_id)

    # Build new config from snapshot
    config_data = dict(template.get("config_snapshot", {}))
    config_data["name"] = new_name
    config_data["created_by"] = current_user.id
    config_data["version"] = "1.0.0"
    config_data["status"] = "pending"
    config_data["api_endpoint"] = None
    config_data["stats"] = None

    config_id = await config_repo.create_config(config_data)

    # Increment template usage count
    await template_repo.increment_usage(template_id)

    # Fetch created config
    config = await config_repo.find_by_id(config_id)
    config = ConfigRepository.serialize_doc(config)

    return config


@router.delete(
    "/{template_id}",
    status_code=status.HTTP_200_OK,
    summary="Delete template",
)
async def delete_template(
    template_id: str,
    current_user: CurrentUser,
    db: AsyncIOMotorDatabase = Depends(get_db),
) -> dict:
    """Delete a template. Only the owner can delete."""
    repo = TemplateRepository(db)

    template = await repo.find_by_id(template_id)
    if not template:
        raise NotFoundException("Template", template_id)

    if template.get("created_by") != current_user.id:
        raise ForbiddenException("Only the template owner can delete it")

    await repo.delete_one(template_id)
    return {"message": "Template deleted successfully"}
