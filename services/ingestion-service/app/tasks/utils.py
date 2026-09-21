"""Utility functions for ingestion tasks."""

import hashlib
import logging
from datetime import datetime
from pathlib import Path
from typing import Any

from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase

from app.core.settings import settings

logger = logging.getLogger(__name__)


# Supported file extensions by processor type
SUPPORTED_EXTENSIONS: dict[str, list[str]] = {
    "text": [".txt", ".md", ".rst", ".log"],
    "pdf": [".pdf"],
    "docx": [".docx", ".doc"],
    "image": [".png", ".jpg", ".jpeg", ".gif", ".bmp", ".tiff", ".webp"],
    "excel": [".xlsx", ".xls", ".csv"],
    "html": [".html", ".htm"],
}


def get_all_supported_extensions() -> set[str]:
    """Get all supported file extensions."""
    all_extensions = set()
    for extensions in SUPPORTED_EXTENSIONS.values():
        all_extensions.update(extensions)
    return all_extensions


def is_supported_file(file_path: str) -> bool:
    """Check if a file has a supported extension."""
    ext = Path(file_path).suffix.lower()
    return ext in get_all_supported_extensions()


def get_processor_type(file_path: str) -> str | None:
    """Get the processor type for a file based on extension."""
    ext = Path(file_path).suffix.lower()
    for processor_type, extensions in SUPPORTED_EXTENSIONS.items():
        if ext in extensions:
            return processor_type
    return None


def compute_file_hash(file_path: str) -> str:
    """Compute MD5 hash of a file for deduplication."""
    hasher = hashlib.md5()
    try:
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(65536), b""):
                hasher.update(chunk)
        return hasher.hexdigest()
    except OSError as e:
        logger.error(f"Failed to hash file {file_path}: {e}")
        return ""


def compute_content_hash(content: str) -> str:
    """Compute MD5 hash of content string."""
    return hashlib.md5(content.encode("utf-8")).hexdigest()


def scan_directory(
    directory: str,
    recursive: bool = True,
    include_extensions: list[str] | None = None,
    exclude_patterns: list[str] | None = None,
) -> list[str]:
    """
    Scan a directory for files.

    Args:
        directory: Directory path to scan
        recursive: Whether to scan subdirectories
        include_extensions: Only include files with these extensions
        exclude_patterns: Exclude files matching these patterns

    Returns:
        List of file paths
    """
    files = []
    directory_path = Path(directory)

    if not directory_path.exists():
        logger.warning(f"Directory does not exist: {directory}")
        return files

    if not directory_path.is_dir():
        logger.warning(f"Path is not a directory: {directory}")
        return files

    # Default to supported extensions if not specified
    if include_extensions is None:
        include_extensions = list(get_all_supported_extensions())

    exclude_patterns = exclude_patterns or []

    try:
        if recursive:
            iterator = directory_path.rglob("*")
        else:
            iterator = directory_path.glob("*")

        for path in iterator:
            if not path.is_file():
                continue

            # Check extension
            if path.suffix.lower() not in include_extensions:
                continue

            # Check exclude patterns
            excluded = False
            path_str = str(path)
            for pattern in exclude_patterns:
                if pattern in path_str:
                    excluded = True
                    break

            if not excluded:
                files.append(str(path))

    except PermissionError as e:
        logger.error(f"Permission denied scanning {directory}: {e}")
    except Exception as e:
        logger.error(f"Error scanning directory {directory}: {e}")

    return sorted(files)


def get_relative_path(file_path: str, base_path: str) -> str:
    """Get the relative path from base to file."""
    try:
        return str(Path(file_path).relative_to(base_path))
    except ValueError:
        return file_path


def get_folder_path(file_path: str, base_path: str) -> str:
    """Get the folder path relative to base for RBAC."""
    try:
        relative = Path(file_path).relative_to(base_path)
        return str(relative.parent)
    except ValueError:
        return str(Path(file_path).parent)


def format_file_size(size_bytes: int) -> str:
    """Format file size in human-readable format."""
    for unit in ["B", "KB", "MB", "GB", "TB"]:
        if size_bytes < 1024:
            return f"{size_bytes:.2f} {unit}"
        size_bytes /= 1024
    return f"{size_bytes:.2f} PB"


def get_file_metadata(file_path: str) -> dict[str, Any]:
    """Get metadata for a file."""
    path = Path(file_path)
    try:
        stat = path.stat()
        return {
            "file_name": path.name,
            "file_path": str(path),
            "file_type": path.suffix.lower(),
            "file_size_bytes": stat.st_size,
            "file_size_formatted": format_file_size(stat.st_size),
            "modified_at": datetime.fromtimestamp(stat.st_mtime).isoformat(),
            "created_at": datetime.fromtimestamp(stat.st_ctime).isoformat(),
        }
    except OSError as e:
        logger.error(f"Failed to get file metadata for {file_path}: {e}")
        return {
            "file_name": path.name,
            "file_path": str(path),
            "file_type": path.suffix.lower(),
        }


def create_sync_mongodb_client() -> AsyncIOMotorClient:
    """Create a MongoDB client for use in Celery tasks."""
    return AsyncIOMotorClient(settings.mongodb_uri)


def get_sync_database(client: AsyncIOMotorClient) -> AsyncIOMotorDatabase:
    """Get the database from a MongoDB client."""
    return client[settings.mongodb_database]


class ProgressTracker:
    """Track progress of an ingestion job."""

    def __init__(
        self,
        total_files: int,
        ingestion_id: str,
        celery_task: Any = None,
    ):
        """
        Initialize progress tracker.

        Args:
            total_files: Total number of files to process
            ingestion_id: Ingestion job ID
            celery_task: Celery task instance for state updates
        """
        self.total_files = total_files
        self.ingestion_id = ingestion_id
        self.celery_task = celery_task

        self.processed_files = 0
        self.failed_files = 0
        self.total_chunks = 0
        self.total_embeddings = 0
        self.graph_nodes = 0
        self.graph_edges = 0
        self.current_step = ""
        self.steps_completed: list[str] = []
        self.errors: list[dict[str, Any]] = []
        self.started_at = datetime.utcnow()

    @property
    def progress_percent(self) -> float:
        """Calculate progress percentage."""
        if self.total_files == 0:
            return 0.0
        return (self.processed_files / self.total_files) * 100

    def file_processed(
        self,
        file_path: str,
        chunks_created: int = 0,
        embeddings_created: int = 0,
    ) -> None:
        """Mark a file as processed."""
        self.processed_files += 1
        self.total_chunks += chunks_created
        self.total_embeddings += embeddings_created
        self._update_celery_state()

    def file_failed(self, file_path: str, error: str) -> None:
        """Mark a file as failed."""
        self.failed_files += 1
        self.errors.append(
            {
                "file_path": file_path,
                "error": error,
                "timestamp": datetime.utcnow().isoformat(),
            }
        )
        self._update_celery_state()

    def set_step(self, step: str) -> None:
        """Set the current processing step."""
        if self.current_step and self.current_step not in self.steps_completed:
            self.steps_completed.append(self.current_step)
        self.current_step = step
        self._update_celery_state()

    def add_graph_stats(self, nodes: int, edges: int) -> None:
        """Add graph statistics."""
        self.graph_nodes += nodes
        self.graph_edges += edges

    def _update_celery_state(self) -> None:
        """Update Celery task state."""
        if self.celery_task:
            try:
                self.celery_task.update_state(
                    state="PROGRESS",
                    meta=self.get_meta(),
                )
            except Exception as e:
                logger.debug(f"Failed to update Celery state: {e}")

    def get_meta(self) -> dict[str, Any]:
        """Get progress metadata."""
        return {
            "ingestion_id": self.ingestion_id,
            "progress": self.progress_percent,
            "current_step": self.current_step,
            "total_files": self.total_files,
            "processed_files": self.processed_files,
            "failed_files": self.failed_files,
            "total_chunks": self.total_chunks,
            "total_embeddings": self.total_embeddings,
            "graph_nodes": self.graph_nodes,
            "graph_edges": self.graph_edges,
        }

    def get_final_stats(self) -> dict[str, Any]:
        """Get final statistics."""
        completed_at = datetime.utcnow()
        duration = (completed_at - self.started_at).total_seconds()

        return {
            "total_files": self.total_files,
            "processed_files": self.processed_files,
            "failed_files": self.failed_files,
            "total_chunks": self.total_chunks,
            "total_embeddings": self.total_embeddings,
            "graph_nodes": self.graph_nodes,
            "graph_edges": self.graph_edges,
            "processing_time_seconds": duration,
            "started_at": self.started_at.isoformat(),
            "completed_at": completed_at.isoformat(),
        }
