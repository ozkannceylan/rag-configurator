"""Celery tasks module."""

# Import utilities (always available)
from app.tasks.utils import (
    ProgressTracker,
    compute_file_hash,
    get_file_metadata,
    get_processor_type,
    is_supported_file,
    scan_directory,
)

# Import Celery tasks only if Celery is available
try:
    from app.tasks.ingestion_task import (
        IngestionPipeline,
        cancel_ingestion,
        get_ingestion_status,
        run_ingestion,
    )

    __all__ = [
        "run_ingestion",
        "cancel_ingestion",
        "get_ingestion_status",
        "IngestionPipeline",
        "ProgressTracker",
        "scan_directory",
        "compute_file_hash",
        "get_file_metadata",
        "is_supported_file",
        "get_processor_type",
    ]
except ImportError:
    # Celery not available, export only utilities
    __all__ = [
        "ProgressTracker",
        "scan_directory",
        "compute_file_hash",
        "get_file_metadata",
        "is_supported_file",
        "get_processor_type",
    ]
