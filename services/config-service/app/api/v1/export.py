"""Configuration export/import endpoints."""

from fastapi import APIRouter, Depends, UploadFile, File, Response, status
from fastapi.responses import PlainTextResponse
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.db.mongodb import get_db
from app.api.deps import CurrentUser
from app.schemas.config import ConfigResponse
from app.services.export_service import ExportService

router = APIRouter(prefix="/configs", tags=["export"])


@router.get(
    "/{config_id}/export",
    response_class=PlainTextResponse,
    summary="Export configuration as YAML",
)
async def export_config(
    config_id: str,
    current_user: CurrentUser,
    db: AsyncIOMotorDatabase = Depends(get_db),
) -> Response:
    """
    Export a configuration as a YAML file.
    """
    service = ExportService(db)
    yaml_content = await service.export_yaml(config_id, current_user.id)

    return Response(
        content=yaml_content,
        media_type="application/x-yaml",
        headers={"Content-Disposition": f"attachment; filename=config-{config_id}.yaml"},
    )


@router.post(
    "/import",
    response_model=ConfigResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Import configuration from YAML",
)
async def import_config(
    current_user: CurrentUser,
    file: UploadFile = File(...),
    db: AsyncIOMotorDatabase = Depends(get_db),
) -> ConfigResponse:
    """
    Import a configuration from a YAML file.
    """
    # Read file content
    content = await file.read()
    yaml_content = content.decode("utf-8")

    service = ExportService(db)
    return await service.import_yaml(yaml_content, current_user.id)
