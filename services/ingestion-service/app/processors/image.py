"""Image processor with OCR and Vision LLM support."""

import base64
import logging
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

from app.processors.base import (
    BaseProcessor,
    DocumentProcessingConfig,
    ProcessedDocument,
)

logger = logging.getLogger(__name__)


class ImageProcessor(BaseProcessor):
    """Processor for image files using OCR or Vision LLM."""

    supported_extensions: List[str] = [
        ".png",
        ".jpg",
        ".jpeg",
        ".gif",
        ".bmp",
        ".tiff",
        ".tif",
        ".webp",
    ]

    async def process(
        self, file_path: Path, config: Optional[DocumentProcessingConfig] = None
    ) -> ProcessedDocument:
        """
        Process an image file and extract text.

        Uses Vision LLM if configured, otherwise falls back to OCR.

        Args:
            file_path: Path to the image file
            config: Optional processing configuration

        Returns:
            ProcessedDocument with extracted text and metadata
        """
        cfg = config or self.config
        start_time = time.time()
        errors: List[str] = []
        warnings: List[str] = []

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

        # Get image dimensions
        try:
            dimensions = self._get_image_dimensions(file_path)
            metadata.update(dimensions)
        except Exception as e:
            warnings.append(f"Could not get image dimensions: {str(e)}")

        content = ""

        # Try Vision LLM first if configured
        if cfg.use_vision_llm:
            try:
                content = await self._process_with_vision_llm(file_path, cfg)
                metadata["processor_method"] = "vision_llm"
                metadata["vision_model"] = cfg.vision_model
            except Exception as e:
                warnings.append(f"Vision LLM failed: {str(e)}, trying OCR")
                if cfg.enable_ocr:
                    try:
                        content = await self._process_with_ocr(file_path, cfg)
                        metadata["processor_method"] = "ocr_fallback"
                    except Exception as e2:
                        errors.append(f"OCR also failed: {str(e2)}")
                else:
                    errors.append(f"Vision LLM failed and OCR disabled: {str(e)}")
        elif cfg.enable_ocr:
            # Use OCR
            try:
                content = await self._process_with_ocr(file_path, cfg)
                metadata["processor_method"] = "ocr"
                metadata["ocr_language"] = cfg.ocr_language
            except Exception as e:
                errors.append(f"OCR failed: {str(e)}")
        else:
            errors.append("Both Vision LLM and OCR are disabled")

        # Calculate processing time
        processing_time = (time.time() - start_time) * 1000

        return ProcessedDocument(
            content=content,
            metadata=metadata,
            pages=1,
            processing_time_ms=processing_time,
            processor_name=self.__class__.__name__,
            errors=errors,
            warnings=warnings,
        )

    def _get_image_dimensions(self, file_path: Path) -> Dict[str, Any]:
        """Get image dimensions using PIL."""
        try:
            from PIL import Image

            with Image.open(file_path) as img:
                return {
                    "width": img.width,
                    "height": img.height,
                    "format": img.format,
                    "mode": img.mode,
                }
        except ImportError:
            raise ImportError("Pillow not installed")

    async def _process_with_vision_llm(
        self, file_path: Path, config: DocumentProcessingConfig
    ) -> str:
        """Process image using Vision LLM (OpenAI GPT-4 Vision)."""
        try:
            from openai import AsyncOpenAI
        except ImportError:
            raise ImportError("OpenAI SDK not installed")

        from app.core.settings import settings

        if not settings.openai_api_key:
            raise ValueError("OpenAI API key not configured")

        # Read and encode image
        image_data = file_path.read_bytes()
        base64_image = base64.b64encode(image_data).decode("utf-8")

        # Determine MIME type
        suffix = file_path.suffix.lower()
        mime_types = {
            ".png": "image/png",
            ".jpg": "image/jpeg",
            ".jpeg": "image/jpeg",
            ".gif": "image/gif",
            ".webp": "image/webp",
        }
        mime_type = mime_types.get(suffix, "image/png")

        # Create OpenAI client
        client = AsyncOpenAI(api_key=settings.openai_api_key)

        # Call Vision API
        response = await client.chat.completions.create(
            model=config.vision_model,
            messages=[
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": (
                                "Extract all text content from this image. "
                                "Include any text visible in the image, maintaining "
                                "the original structure and formatting as much as possible. "
                                "If there are tables, preserve the table structure. "
                                "If there are diagrams with labels, include those labels. "
                                "Only output the extracted text, no explanations."
                            ),
                        },
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:{mime_type};base64,{base64_image}",
                            },
                        },
                    ],
                }
            ],
            max_tokens=4096,
        )

        return response.choices[0].message.content or ""

    async def _process_with_ocr(
        self, file_path: Path, config: DocumentProcessingConfig
    ) -> str:
        """Process image using Tesseract OCR."""
        try:
            import pytesseract
            from PIL import Image
        except ImportError:
            raise ImportError("pytesseract or Pillow not installed")

        # Open image with PIL
        with Image.open(file_path) as img:
            # Convert to RGB if necessary
            if img.mode not in ("L", "RGB"):
                img = img.convert("RGB")

            # Perform OCR
            text = pytesseract.image_to_string(img, lang=config.ocr_language)

        return text.strip()
