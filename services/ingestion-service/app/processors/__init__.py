"""Document processors for extracting text from various file types."""

from app.processors.base import BaseProcessor, ProcessedDocument
from app.processors.factory import get_processor, get_supported_extensions

__all__ = [
    "BaseProcessor",
    "ProcessedDocument",
    "get_processor",
    "get_supported_extensions",
]
