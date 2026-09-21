"""Folder scanning endpoints."""

from pathlib import Path

from fastapi import APIRouter, HTTPException, status

from app.api.deps import CurrentUser
from app.schemas.folder import (
    BrowseEntry,
    FolderBrowseRequest,
    FolderBrowseResponse,
    FolderScanRequest,
    FolderScanResponse,
)
from app.services.folder_service import FolderService

router = APIRouter(prefix="/folders", tags=["folders"])

# Allowed root paths for browsing (security: prevent arbitrary filesystem access)
BROWSE_ROOTS = [
    Path("/data/local"),  # Mounted from LOCAL_DATA_PATH
    Path("/app/sample-docs"),  # Demo sample docs
    Path("/data"),  # General data directory
]


@router.post(
    "/browse",
    response_model=FolderBrowseResponse,
    summary="Browse directories",
)
async def browse_folders(
    request: FolderBrowseRequest,
    current_user: CurrentUser,
) -> FolderBrowseResponse:
    """
    Browse directories at a given path for folder selection.

    If path is empty, returns the available root directories.
    Otherwise lists subdirectories at the given path.
    """
    try:
        # If no path given, return available roots
        if not request.path:
            entries = []
            for root in BROWSE_ROOTS:
                if root.exists() and root.is_dir():
                    has_children = (
                        any(
                            item.is_dir() and not item.name.startswith(".")
                            for item in root.iterdir()
                        )
                        if root.exists()
                        else False
                    )
                    entries.append(
                        BrowseEntry(
                            name=root.name,
                            path=str(root),
                            type="folder",
                            has_children=has_children,
                        )
                    )
            return FolderBrowseResponse(
                current_path="/",
                parent_path=None,
                entries=entries,
            )

        browse_path = Path(request.path).resolve()

        # Security: ensure path is under one of the allowed roots
        allowed = False
        for root in BROWSE_ROOTS:
            if root.exists():
                try:
                    browse_path.relative_to(root.resolve())
                    allowed = True
                    break
                except ValueError:
                    continue
        # Also allow the roots themselves
        if not allowed:
            for root in BROWSE_ROOTS:
                if root.exists() and browse_path == root.resolve():
                    allowed = True
                    break

        if not allowed:
            raise ValueError(
                f"Access denied: path must be under one of: {[str(r) for r in BROWSE_ROOTS]}"
            )

        if not browse_path.exists():
            raise ValueError(f"Path does not exist: {request.path}")

        if not browse_path.is_dir():
            raise ValueError(f"Path is not a directory: {request.path}")

        # List subdirectories
        entries = []
        for item in sorted(browse_path.iterdir()):
            if item.name.startswith("."):
                continue
            if item.is_dir():
                has_children = (
                    any(
                        child.is_dir() and not child.name.startswith(".")
                        for child in item.iterdir()
                    )
                    if item.is_dir()
                    else False
                )
                entries.append(
                    BrowseEntry(
                        name=item.name,
                        path=str(item),
                        type="folder",
                        has_children=has_children,
                    )
                )

        # Calculate parent path (if not at a root)
        parent_path = str(browse_path.parent)
        is_root = any(
            browse_path == root.resolve() for root in BROWSE_ROOTS if root.exists()
        )
        if is_root:
            parent_path = ""  # Go back to root listing

        return FolderBrowseResponse(
            current_path=str(browse_path),
            parent_path=parent_path,
            entries=entries,
        )

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    except PermissionError:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Permission denied to access this path",
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to browse path: {str(e)}",
        )


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
