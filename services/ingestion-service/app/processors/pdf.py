"""PDF processor using Docling with PyMuPDF fallback."""

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


class PDFProcessor(BaseProcessor):
    """Processor for PDF files using Docling with PyMuPDF fallback."""

    supported_extensions: list[str] = [".pdf"]

    async def process(
        self, file_path: Path, config: DocumentProcessingConfig | None = None
    ) -> ProcessedDocument:
        """
        Process a PDF file and extract content.

        Primary: Docling for structure extraction (tables, headers)
        Fallback: PyMuPDF for basic text extraction

        Args:
            file_path: Path to the PDF file
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

        # Try Docling first for better structure extraction
        content = ""
        pages = 0
        tables: list[dict[str, Any]] = []
        sections: list[dict[str, Any]] = []

        try:
            result = await self._process_with_docling(file_path, cfg)
            content = result.get("content", "")
            pages = result.get("pages", 0)
            tables = result.get("tables", [])
            sections = result.get("sections", [])
            metadata.update(result.get("metadata", {}))
            metadata["processor_method"] = "docling"
        except ImportError:
            warnings.append("Docling not available, using PyMuPDF fallback")
            try:
                result = await self._process_with_pymupdf(file_path, cfg)
                content = result.get("content", "")
                pages = result.get("pages", 0)
                metadata.update(result.get("metadata", {}))
                metadata["processor_method"] = "pymupdf"
            except ImportError:
                errors.append("Neither Docling nor PyMuPDF available")
            except Exception as e:
                errors.append(f"PyMuPDF processing failed: {str(e)}")
        except Exception as e:
            warnings.append(f"Docling failed: {str(e)}, trying PyMuPDF")
            try:
                result = await self._process_with_pymupdf(file_path, cfg)
                content = result.get("content", "")
                pages = result.get("pages", 0)
                metadata.update(result.get("metadata", {}))
                metadata["processor_method"] = "pymupdf_fallback"
            except Exception as e2:
                errors.append(f"All PDF processors failed. PyMuPDF error: {str(e2)}")

        # Calculate processing time
        processing_time = (time.time() - start_time) * 1000

        return ProcessedDocument(
            content=content,
            metadata=metadata,
            pages=pages,
            tables=tables,
            sections=sections,
            processing_time_ms=processing_time,
            processor_name=self.__class__.__name__,
            errors=errors,
            warnings=warnings,
        )

    async def _process_with_docling(
        self, file_path: Path, config: DocumentProcessingConfig
    ) -> dict[str, Any]:
        """Process PDF using Docling for structure extraction."""
        try:
            from docling.datamodel.pipeline_options import PdfPipelineOptions
            from docling.document_converter import DocumentConverter
        except ImportError as err:
            raise ImportError("Docling not installed") from err

        # Configure Docling pipeline
        pipeline_options = PdfPipelineOptions()
        pipeline_options.do_ocr = config.enable_ocr
        pipeline_options.do_table_structure = config.extract_tables

        converter = DocumentConverter()
        result = converter.convert(str(file_path))

        # Extract content
        content_parts = []
        tables = []
        sections = []

        # Get document
        doc = result.document

        # Extract text content
        content = doc.export_to_markdown() if hasattr(doc, "export_to_markdown") else ""

        # If markdown export not available, extract text
        if not content and hasattr(doc, "texts"):
            content_parts = [text.text for text in doc.texts if hasattr(text, "text")]
            content = "\n\n".join(content_parts)

        # Extract tables if available
        if config.extract_tables and hasattr(doc, "tables"):
            for i, table in enumerate(doc.tables):
                table_data = {
                    "index": i,
                    "content": str(table) if table else "",
                }
                tables.append(table_data)

        # Extract metadata
        metadata = {}
        if hasattr(result, "metadata"):
            metadata = dict(result.metadata) if result.metadata else {}

        return {
            "content": content,
            "pages": getattr(doc, "num_pages", 1),
            "tables": tables,
            "sections": sections,
            "metadata": metadata,
        }

    async def _process_with_pymupdf(
        self, file_path: Path, config: DocumentProcessingConfig
    ) -> dict[str, Any]:
        """Process PDF using PyMuPDF as fallback."""
        try:
            import fitz  # PyMuPDF
        except ImportError as err:
            raise ImportError("PyMuPDF (fitz) not installed") from err

        doc = fitz.open(str(file_path))
        content_parts = []
        metadata = {}

        try:
            # Extract metadata
            pdf_metadata = doc.metadata
            if pdf_metadata:
                metadata = {
                    "title": pdf_metadata.get("title", ""),
                    "author": pdf_metadata.get("author", ""),
                    "subject": pdf_metadata.get("subject", ""),
                    "keywords": pdf_metadata.get("keywords", ""),
                    "creator": pdf_metadata.get("creator", ""),
                    "producer": pdf_metadata.get("producer", ""),
                    "creation_date": pdf_metadata.get("creationDate", ""),
                    "modification_date": pdf_metadata.get("modDate", ""),
                }

            # Extract text from each page
            for page_num in range(len(doc)):
                page = doc[page_num]
                text = page.get_text("text")
                if text.strip():
                    content_parts.append(text)

            pages = len(doc)
        finally:
            doc.close()

        content = "\n\n".join(content_parts)

        return {
            "content": content,
            "pages": pages,
            "tables": [],
            "sections": [],
            "metadata": metadata,
        }
