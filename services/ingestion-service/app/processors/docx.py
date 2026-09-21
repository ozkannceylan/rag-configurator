"""Word document processor for .docx files."""

import logging
import time
from pathlib import Path
from typing import Any

from app.processors.base import (
    BaseProcessor,
    DocumentProcessingConfig,
    ProcessedDocument,
)

logger = logging.getLogger(__name__)


class DocxProcessor(BaseProcessor):
    """Processor for Microsoft Word documents (.docx)."""

    supported_extensions: list[str] = [".docx"]

    async def process(
        self, file_path: Path, config: DocumentProcessingConfig | None = None
    ) -> ProcessedDocument:
        """
        Process a Word document and extract content.

        Args:
            file_path: Path to the .docx file
            config: Optional processing configuration

        Returns:
            ProcessedDocument with extracted content and metadata
        """
        cfg = config or self.config
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

        content = ""
        tables: list[dict[str, Any]] = []
        sections: list[dict[str, Any]] = []

        try:
            from docx import Document
            from docx.opc.exceptions import PackageNotFoundError
        except ImportError:
            return ProcessedDocument(
                content="",
                errors=["python-docx not installed"],
                processor_name=self.__class__.__name__,
            )

        try:
            doc = Document(str(file_path))
        except PackageNotFoundError:
            return ProcessedDocument(
                content="",
                errors=["Invalid or corrupted .docx file"],
                metadata=metadata,
                processor_name=self.__class__.__name__,
            )
        except Exception as e:
            return ProcessedDocument(
                content="",
                errors=[f"Failed to open document: {str(e)}"],
                metadata=metadata,
                processor_name=self.__class__.__name__,
            )

        # Extract document properties
        if cfg.extract_metadata:
            try:
                core_props = doc.core_properties
                metadata.update(
                    {
                        "title": core_props.title or "",
                        "author": core_props.author or "",
                        "subject": core_props.subject or "",
                        "keywords": core_props.keywords or "",
                        "created": (
                            core_props.created.isoformat()
                            if core_props.created
                            else None
                        ),
                        "modified": (
                            core_props.modified.isoformat()
                            if core_props.modified
                            else None
                        ),
                        "last_modified_by": core_props.last_modified_by or "",
                        "revision": core_props.revision,
                    }
                )
            except Exception as e:
                warnings.append(f"Could not extract document properties: {str(e)}")

        # Extract paragraphs
        content_parts = []
        for para in doc.paragraphs:
            text = para.text.strip()
            if text:
                content_parts.append(text)

            # Track headings for sections
            if para.style and para.style.name.startswith("Heading"):
                try:
                    level = int(para.style.name.replace("Heading ", ""))
                except ValueError:
                    level = 1

                sections.append(
                    {
                        "level": level,
                        "title": text,
                        "style": para.style.name,
                    }
                )

        # Extract tables
        if cfg.extract_tables:
            for i, table in enumerate(doc.tables):
                try:
                    table_data = self._extract_table(table)
                    tables.append(
                        {
                            "index": i,
                            "rows": len(table.rows),
                            "columns": len(table.columns),
                            "data": table_data,
                            "text": self._table_to_text(table_data),
                        }
                    )
                    # Add table text to content
                    content_parts.append(f"\n[Table {i + 1}]\n{tables[-1]['text']}")
                except Exception as e:
                    warnings.append(f"Failed to extract table {i}: {str(e)}")

        content = "\n\n".join(content_parts)

        # Count pages (estimate based on content)
        # Word doesn't store page count in the file
        metadata["paragraph_count"] = len(doc.paragraphs)
        metadata["table_count"] = len(doc.tables)
        metadata["section_count"] = len(sections)

        # Calculate processing time
        processing_time = (time.time() - start_time) * 1000

        return ProcessedDocument(
            content=content,
            metadata=metadata,
            pages=1,  # Cannot determine actual page count from .docx
            tables=tables,
            sections=sections,
            processing_time_ms=processing_time,
            processor_name=self.__class__.__name__,
            errors=errors,
            warnings=warnings,
        )

    def _extract_table(self, table) -> list[list[str]]:
        """Extract table data as a 2D list."""
        data = []
        for row in table.rows:
            row_data = []
            for cell in row.cells:
                row_data.append(cell.text.strip())
            data.append(row_data)
        return data

    def _table_to_text(self, table_data: list[list[str]]) -> str:
        """Convert table data to text representation."""
        if not table_data:
            return ""

        # Calculate column widths
        col_widths = []
        for row in table_data:
            for i, cell in enumerate(row):
                if i >= len(col_widths):
                    col_widths.append(len(cell))
                else:
                    col_widths[i] = max(col_widths[i], len(cell))

        # Build text representation
        lines = []
        for row_idx, row in enumerate(table_data):
            cells = []
            for i, cell in enumerate(row):
                width = col_widths[i] if i < len(col_widths) else len(cell)
                cells.append(cell.ljust(width))
            lines.append(" | ".join(cells))

            # Add separator after header row
            if row_idx == 0:
                separators = ["-" * w for w in col_widths]
                lines.append("-+-".join(separators))

        return "\n".join(lines)
