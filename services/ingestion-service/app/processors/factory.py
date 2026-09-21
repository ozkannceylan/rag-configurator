"""Factory for creating document processors based on file type."""

import logging
from pathlib import Path

from app.processors.base import BaseProcessor, DocumentProcessingConfig
from app.processors.docx import DocxProcessor
from app.processors.image import ImageProcessor
from app.processors.pdf import PDFProcessor
from app.processors.text import TextProcessor

logger = logging.getLogger(__name__)

# Registry of processors by file extension
PROCESSOR_REGISTRY: dict[str, type[BaseProcessor]] = {}


def _register_processors() -> None:
    """Register all processors in the registry."""
    processors: list[type[BaseProcessor]] = [
        TextProcessor,
        PDFProcessor,
        ImageProcessor,
        DocxProcessor,
    ]

    for processor_class in processors:
        for ext in processor_class.supported_extensions:
            PROCESSOR_REGISTRY[ext.lower()] = processor_class
            logger.debug(f"Registered {processor_class.__name__} for {ext}")


# Initialize registry on module load
_register_processors()


def get_processor(
    file_path: Path | str,
    config: DocumentProcessingConfig | None = None,
) -> BaseProcessor:
    """
    Get the appropriate processor for a file.

    Args:
        file_path: Path to the file or file path string
        config: Optional processing configuration

    Returns:
        BaseProcessor instance for the file type

    Raises:
        ValueError: If no processor is available for the file type
    """
    if isinstance(file_path, str):
        file_path = Path(file_path)

    extension = file_path.suffix.lower()

    processor_class = PROCESSOR_REGISTRY.get(extension)
    if processor_class is None:
        supported = get_supported_extensions()
        raise ValueError(
            f"No processor available for extension '{extension}'. "
            f"Supported extensions: {supported}"
        )

    return processor_class(config)


def get_supported_extensions() -> list[str]:
    """Get list of all supported file extensions."""
    return sorted(PROCESSOR_REGISTRY.keys())


def get_processor_for_extension(extension: str) -> type[BaseProcessor] | None:
    """
    Get the processor class for a specific extension.

    Args:
        extension: File extension (with or without leading dot)

    Returns:
        Processor class or None if not supported
    """
    if not extension.startswith("."):
        extension = f".{extension}"
    return PROCESSOR_REGISTRY.get(extension.lower())


def is_supported(file_path: Path | str) -> bool:
    """
    Check if a file type is supported.

    Args:
        file_path: Path to the file

    Returns:
        True if the file type is supported
    """
    if isinstance(file_path, str):
        file_path = Path(file_path)

    return file_path.suffix.lower() in PROCESSOR_REGISTRY


def get_processor_info() -> dict[str, dict]:
    """
    Get information about all registered processors.

    Returns:
        Dictionary with processor information
    """
    info = {}

    # Group extensions by processor
    processor_extensions: dict[type[BaseProcessor], list[str]] = {}
    for ext, processor_class in PROCESSOR_REGISTRY.items():
        if processor_class not in processor_extensions:
            processor_extensions[processor_class] = []
        processor_extensions[processor_class].append(ext)

    for processor_class, extensions in processor_extensions.items():
        info[processor_class.__name__] = {
            "extensions": sorted(extensions),
            "description": processor_class.__doc__ or "",
        }

    return info
