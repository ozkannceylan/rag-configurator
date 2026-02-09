"""Folder scanning schemas."""

from typing import List, Optional
from pydantic import BaseModel, Field

from rag_config_common.models.enums import DataType, DataSourceType


class FolderScanRequest(BaseModel):
    """Request to scan a folder."""

    type: DataSourceType = DataSourceType.LOCAL
    base_path: str = Field(..., description="Path to scan")
    credentials: Optional[dict] = Field(None, description="Cloud credentials if needed")


class FolderBrowseRequest(BaseModel):
    """Request to browse directories at a given path."""

    path: str = Field(default="", description="Path to browse (empty for roots)")


class BrowseEntry(BaseModel):
    """A directory entry in browse results."""

    name: str
    path: str
    type: str = "folder"  # folder or file
    has_children: bool = False


class FolderBrowseResponse(BaseModel):
    """Response with browsable directory listing."""

    current_path: str
    parent_path: Optional[str] = None
    entries: List[BrowseEntry]


class FolderInfo(BaseModel):
    """Information about a scanned folder."""

    path: str
    name: str
    detected_types: List[DataType] = []
    file_count: int = 0
    children: List["FolderInfo"] = []


class FolderScanResponse(BaseModel):
    """Response from folder scan."""

    base_path: str
    folders: List[FolderInfo]
    has_multimodal: bool


# Update forward refs for recursive model
FolderInfo.model_rebuild()
