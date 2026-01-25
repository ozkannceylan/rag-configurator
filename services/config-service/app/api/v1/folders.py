"""Folder scanning endpoints."""

from fastapi import APIRouter, HTTPException, status

from app.api.deps import CurrentUser
from app.schemas.folder import FolderScanRequest, FolderScanResponse
from app.services.folder_service import FolderService

router = APIRouter(prefix="/folders", tags=["folders"])


@router.post(
    "/scan",
    response_model=FolderScanResponse,
    summary="Scan folder structure",
)
async def scan_folders(
    request: FolderScanRequest,
    current_user: CurrentUser,
) -> FolderScanResponse:
    """
    Scan a directory and return its structure with detected file types.

    Currently supports local file system. Cloud storage support coming soon.
    """
    try:
        service = FolderService()
        return service.scan(request)
    except NotImplementedError as e:
        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED,
            detail=str(e),
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to scan folder: {str(e)}",
        )
