"""Folder scanning service."""

from pathlib import Path
from typing import List, Set

from rag_config_common.models.enums import DataType

from app.schemas.folder import FolderInfo, FolderScanResponse, FolderScanRequest


# File extension to DataType mapping
EXTENSION_MAP = {
    ".txt": DataType.TEXT,
    ".md": DataType.MARKDOWN,
    ".markdown": DataType.MARKDOWN,
    ".pdf": DataType.PDF,
    ".png": DataType.IMAGE,
    ".jpg": DataType.IMAGE,
    ".jpeg": DataType.IMAGE,
    ".gif": DataType.IMAGE,
    ".webp": DataType.IMAGE,
    ".docx": DataType.DOCX,
    ".doc": DataType.DOCX,
    ".xlsx": DataType.XLSX,
    ".xls": DataType.XLSX,
    ".csv": DataType.CSV,
}

# Image/complex file types that indicate multimodal
MULTIMODAL_TYPES = {DataType.IMAGE, DataType.PDF}


class FolderService:
    """Service for scanning and analyzing folders."""

    def scan(self, request: FolderScanRequest) -> FolderScanResponse:
        """
        Scan a directory and return folder structure with detected file types.

        Currently supports local file system only.
        """
        if request.type != "local":
            raise NotImplementedError(
                f"Data source type '{request.type}' not yet supported"
            )

        base_path = Path(request.base_path)

        if not base_path.exists():
            raise ValueError(f"Path does not exist: {request.base_path}")

        if not base_path.is_dir():
            raise ValueError(f"Path is not a directory: {request.base_path}")

        # Scan folder recursively
        folders, all_types = self._scan_directory(base_path, base_path)

        # Determine if multimodal content exists
        has_multimodal = bool(all_types & MULTIMODAL_TYPES)

        return FolderScanResponse(
            base_path=str(base_path.absolute()),
            folders=folders,
            has_multimodal=has_multimodal,
        )

    def _scan_directory(
        self,
        path: Path,
        base_path: Path,
        max_depth: int = 5,
        current_depth: int = 0,
    ) -> tuple[List[FolderInfo], Set[DataType]]:
        """
        Recursively scan a directory.

        Returns tuple of (folder_infos, all_detected_types).
        """
        if current_depth >= max_depth:
            return [], set()

        folders = []
        all_types: Set[DataType] = set()

        try:
            for item in sorted(path.iterdir()):
                # Skip hidden files/folders
                if item.name.startswith("."):
                    continue

                if item.is_dir():
                    # Recursively scan subdirectory
                    children, child_types = self._scan_directory(
                        item, base_path, max_depth, current_depth + 1
                    )

                    # Get direct files in this folder
                    detected_types, file_count = self._analyze_folder(item)

                    # Combine types from this folder and children
                    combined_types = detected_types | child_types
                    all_types |= combined_types

                    # Calculate relative path
                    rel_path = str(item.relative_to(base_path))

                    folders.append(
                        FolderInfo(
                            path=rel_path,
                            name=item.name,
                            detected_types=list(combined_types),
                            file_count=file_count,
                            children=children,
                        )
                    )
        except PermissionError:
            pass  # Skip folders we can't access

        return folders, all_types

    def _analyze_folder(self, path: Path) -> tuple[Set[DataType], int]:
        """
        Analyze files directly in a folder (not recursive).

        Returns tuple of (detected_types, file_count).
        """
        detected_types: Set[DataType] = set()
        file_count = 0

        try:
            for item in path.iterdir():
                if item.is_file() and not item.name.startswith("."):
                    file_count += 1
                    ext = item.suffix.lower()
                    if ext in EXTENSION_MAP:
                        detected_types.add(EXTENSION_MAP[ext])
        except PermissionError:
            pass

        return detected_types, file_count
