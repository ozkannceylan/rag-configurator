"""Text processor for plain text and markdown files."""

import logging
import time
from pathlib import Path

from app.processors.base import (
    BaseProcessor,
    DocumentProcessingConfig,
    ProcessedDocument,
)

logger = logging.getLogger(__name__)


class TextProcessor(BaseProcessor):
    """Processor for plain text and markdown files."""

    supported_extensions: list[str] = [".txt", ".md", ".markdown", ".rst", ".text"]

    # Common encodings to try
    ENCODINGS = ["utf-8", "utf-8-sig", "latin-1", "cp1252", "iso-8859-1"]

    async def process(
        self, file_path: Path, config: DocumentProcessingConfig | None = None
    ) -> ProcessedDocument:
        """
        Process a text file and extract content.

        Args:
            file_path: Path to the text file
            config: Optional processing configuration

        Returns:
            ProcessedDocument with text content and metadata
        """
        start_time = time.time()
        errors: list[str] = []
        warnings: list[str] = []

        # Validate file
        try:
            self.validate_file(file_path)
        except Exception as e:
            return ProcessedDocument(
                content="",
                errors=[str(e)],
                processor_name=self.__class__.__name__,
            )

        # Get file metadata
        metadata = self.get_file_metadata(file_path)

        # Read file content with encoding detection
        content = ""
        encoding_used = None

        for encoding in self.ENCODINGS:
            try:
                content = file_path.read_text(encoding=encoding)
                encoding_used = encoding
                break
            except UnicodeDecodeError:
                continue
            except Exception as e:
                errors.append(f"Error reading with {encoding}: {str(e)}")

        if not content and not errors:
            errors.append(f"Could not decode file with any encoding: {self.ENCODINGS}")

        # Add encoding info to metadata
        metadata["encoding"] = encoding_used

        # Extract text statistics
        lines = content.split("\n") if content else []
        metadata["line_count"] = len(lines)
        metadata["empty_line_count"] = sum(1 for line in lines if not line.strip())

        # Detect if markdown
        is_markdown = file_path.suffix.lower() in [".md", ".markdown"]
        metadata["is_markdown"] = is_markdown

        # Extract sections for markdown
        sections = []
        if is_markdown and content:
            sections = self._extract_markdown_sections(content)

        # Normalize line endings
        content = content.replace("\r\n", "\n").replace("\r", "\n")

        # Calculate processing time
        processing_time = (time.time() - start_time) * 1000

        return ProcessedDocument(
            content=content,
            metadata=metadata,
            pages=1,
            sections=sections,
            processing_time_ms=processing_time,
            processor_name=self.__class__.__name__,
            errors=errors,
            warnings=warnings,
        )

    def _extract_markdown_sections(self, content: str) -> list[dict]:
        """Extract section headers from markdown content."""
        sections = []
        lines = content.split("\n")

        for i, line in enumerate(lines):
            line = line.strip()
            if line.startswith("#"):
                # Count heading level
                level = 0
                for char in line:
                    if char == "#":
                        level += 1
                    else:
                        break

                # Extract title
                title = line[level:].strip()
                if title:
                    sections.append(
                        {
                            "level": level,
                            "title": title,
                            "line_number": i + 1,
                        }
                    )

        return sections
