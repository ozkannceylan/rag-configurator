"""Base processor interface and common data structures."""

import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class DocumentProcessingConfig:
    """Configuration for document processing."""

    # OCR settings
    enable_ocr: bool = True
    ocr_language: str = "eng"

    # PDF settings
    extract_images: bool = False
    extract_tables: bool = True

    # Image settings
    use_vision_llm: bool = False
    vision_model: str = "gpt-4o-mini"

    # General settings
    max_file_size_mb: int = 100
    timeout_seconds: int = 300

    # Metadata extraction
    extract_metadata: bool = True


@dataclass
class ProcessedDocument:
    """Result of document processing."""

    content: str
    metadata: Dict[str, Any] = field(default_factory=dict)
    pages: int = 1
    sections: List[Dict[str, Any]] = field(default_factory=list)
    tables: List[Dict[str, Any]] = field(default_factory=list)
    images: List[Dict[str, Any]] = field(default_factory=list)
    processing_time_ms: float = 0.0
    processor_name: str = ""
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)

    @property
    def success(self) -> bool:
        """Check if processing was successful."""
        return len(self.content) > 0 and len(self.errors) == 0

    @property
    def word_count(self) -> int:
        """Get approximate word count."""
        return len(self.content.split())

    @property
    def char_count(self) -> int:
        """Get character count."""
        return len(self.content)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "content": self.content,
            "metadata": self.metadata,
            "pages": self.pages,
            "sections": self.sections,
            "tables": self.tables,
            "images": self.images,
            "processing_time_ms": self.processing_time_ms,
            "processor_name": self.processor_name,
            "word_count": self.word_count,
            "char_count": self.char_count,
            "success": self.success,
            "errors": self.errors,
            "warnings": self.warnings,
        }


class BaseProcessor(ABC):
    """Abstract base class for document processors."""

    # File extensions this processor handles
    supported_extensions: List[str] = []

    def __init__(self, config: Optional[DocumentProcessingConfig] = None):
        """Initialize processor with optional config."""
        self.config = config or DocumentProcessingConfig()
        self.logger = logging.getLogger(self.__class__.__name__)

    @abstractmethod
    async def process(
        self, file_path: Path, config: Optional[DocumentProcessingConfig] = None
    ) -> ProcessedDocument:
        """
        Process a document and extract text content.

        Args:
            file_path: Path to the document file
            config: Optional processing configuration (overrides instance config)

        Returns:
            ProcessedDocument with extracted content and metadata
        """
        pass

    def can_process(self, file_path: Path) -> bool:
        """Check if this processor can handle the given file."""
        return file_path.suffix.lower() in self.supported_extensions

    def get_file_metadata(self, file_path: Path) -> Dict[str, Any]:
        """Extract basic file metadata."""
        stat = file_path.stat()
        return {
            "file_name": file_path.name,
            "file_path": str(file_path),
            "file_extension": file_path.suffix.lower(),
            "file_size_bytes": stat.st_size,
            "file_size_mb": round(stat.st_size / (1024 * 1024), 2),
            "created_at": datetime.fromtimestamp(stat.st_ctime).isoformat(),
            "modified_at": datetime.fromtimestamp(stat.st_mtime).isoformat(),
        }

    def validate_file(self, file_path: Path) -> None:
        """Validate file before processing."""
        if not file_path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")

        if not file_path.is_file():
            raise ValueError(f"Path is not a file: {file_path}")

        # Check file size
        size_mb = file_path.stat().st_size / (1024 * 1024)
        if size_mb > self.config.max_file_size_mb:
            raise ValueError(
                f"File too large: {size_mb:.2f}MB (max: {self.config.max_file_size_mb}MB)"
            )

        # Check extension
        if not self.can_process(file_path):
            raise ValueError(
                f"Unsupported file type: {file_path.suffix}. "
                f"Supported: {self.supported_extensions}"
            )
