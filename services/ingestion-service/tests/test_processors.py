"""Tests for document processors."""

import tempfile
from pathlib import Path

import pytest

from app.processors.base import DocumentProcessingConfig, ProcessedDocument
from app.processors.factory import (
    get_processor,
    get_supported_extensions,
    is_supported,
)
from app.processors.text import TextProcessor


class TestProcessedDocument:
    """Tests for ProcessedDocument dataclass."""

    def test_success_with_content(self):
        """Test success property when content exists."""
        doc = ProcessedDocument(content="Hello world")
        assert doc.success is True

    def test_success_with_errors(self):
        """Test success property when errors exist."""
        doc = ProcessedDocument(content="Hello world", errors=["Some error"])
        assert doc.success is False

    def test_success_with_empty_content(self):
        """Test success property with empty content."""
        doc = ProcessedDocument(content="")
        assert doc.success is False

    def test_word_count(self):
        """Test word count calculation."""
        doc = ProcessedDocument(content="Hello world how are you")
        assert doc.word_count == 5

    def test_char_count(self):
        """Test character count."""
        doc = ProcessedDocument(content="Hello")
        assert doc.char_count == 5

    def test_to_dict(self):
        """Test conversion to dictionary."""
        doc = ProcessedDocument(
            content="Test content",
            metadata={"key": "value"},
            pages=5,
        )
        result = doc.to_dict()

        assert result["content"] == "Test content"
        assert result["metadata"] == {"key": "value"}
        assert result["pages"] == 5
        assert result["success"] is True


class TestDocumentProcessingConfig:
    """Tests for DocumentProcessingConfig."""

    def test_default_values(self):
        """Test default configuration values."""
        config = DocumentProcessingConfig()

        assert config.enable_ocr is True
        assert config.ocr_language == "eng"
        assert config.extract_tables is True
        assert config.use_vision_llm is False
        assert config.max_file_size_mb == 100

    def test_custom_values(self):
        """Test custom configuration values."""
        config = DocumentProcessingConfig(
            enable_ocr=False,
            ocr_language="deu",
            use_vision_llm=True,
            vision_model="gpt-4o",
        )

        assert config.enable_ocr is False
        assert config.ocr_language == "deu"
        assert config.use_vision_llm is True
        assert config.vision_model == "gpt-4o"


class TestTextProcessor:
    """Tests for TextProcessor."""

    @pytest.fixture
    def processor(self):
        """Create text processor instance."""
        return TextProcessor()

    @pytest.fixture
    def temp_text_file(self):
        """Create a temporary text file."""
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".txt", delete=False, encoding="utf-8"
        ) as f:
            f.write("Hello, World!\nThis is a test file.\n")
            return Path(f.name)

    @pytest.fixture
    def temp_markdown_file(self):
        """Create a temporary markdown file."""
        content = """# Heading 1

Some content here.

## Heading 2

More content.

### Heading 3

Even more content.
"""
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".md", delete=False, encoding="utf-8"
        ) as f:
            f.write(content)
            return Path(f.name)

    def test_supported_extensions(self, processor):
        """Test supported extensions."""
        assert ".txt" in processor.supported_extensions
        assert ".md" in processor.supported_extensions
        assert ".markdown" in processor.supported_extensions

    def test_can_process(self, processor, temp_text_file):
        """Test can_process method."""
        assert processor.can_process(temp_text_file) is True
        assert processor.can_process(Path("test.pdf")) is False

    @pytest.mark.asyncio
    async def test_process_text_file(self, processor, temp_text_file):
        """Test processing a text file."""
        result = await processor.process(temp_text_file)

        assert result.success is True
        assert "Hello, World!" in result.content
        assert result.metadata["file_extension"] == ".txt"
        assert result.metadata["line_count"] == 3
        assert result.processor_name == "TextProcessor"

        # Cleanup
        temp_text_file.unlink()

    @pytest.mark.asyncio
    async def test_process_markdown_file(self, processor, temp_markdown_file):
        """Test processing a markdown file."""
        result = await processor.process(temp_markdown_file)

        assert result.success is True
        assert "# Heading 1" in result.content
        assert result.metadata["is_markdown"] is True
        assert len(result.sections) == 3  # 3 headings

        # Check section extraction
        assert result.sections[0]["level"] == 1
        assert result.sections[0]["title"] == "Heading 1"
        assert result.sections[1]["level"] == 2
        assert result.sections[2]["level"] == 3

        # Cleanup
        temp_markdown_file.unlink()

    @pytest.mark.asyncio
    async def test_process_nonexistent_file(self, processor):
        """Test processing a non-existent file."""
        result = await processor.process(Path("/nonexistent/file.txt"))

        assert result.success is False
        assert len(result.errors) > 0

    @pytest.mark.asyncio
    async def test_file_metadata(self, processor, temp_text_file):
        """Test file metadata extraction."""
        result = await processor.process(temp_text_file)

        assert "file_name" in result.metadata
        assert "file_size_bytes" in result.metadata
        assert "created_at" in result.metadata
        assert "modified_at" in result.metadata

        # Cleanup
        temp_text_file.unlink()


class TestProcessorFactory:
    """Tests for processor factory."""

    def test_get_supported_extensions(self):
        """Test getting supported extensions."""
        extensions = get_supported_extensions()

        assert ".txt" in extensions
        assert ".pdf" in extensions
        assert ".png" in extensions
        assert ".docx" in extensions

    def test_is_supported(self):
        """Test is_supported function."""
        assert is_supported(Path("test.txt")) is True
        assert is_supported(Path("test.pdf")) is True
        assert is_supported(Path("test.xyz")) is False
        assert is_supported("document.docx") is True

    def test_get_processor_text(self):
        """Test getting processor for text file."""
        processor = get_processor(Path("test.txt"))
        assert isinstance(processor, TextProcessor)

    def test_get_processor_with_config(self):
        """Test getting processor with custom config."""
        config = DocumentProcessingConfig(enable_ocr=False)
        processor = get_processor(Path("test.txt"), config)

        assert processor.config.enable_ocr is False

    def test_get_processor_unsupported(self):
        """Test getting processor for unsupported file."""
        with pytest.raises(ValueError) as exc_info:
            get_processor(Path("test.unsupported"))

        assert "No processor available" in str(exc_info.value)

    def test_get_processor_from_string_path(self):
        """Test getting processor from string path."""
        processor = get_processor("document.txt")
        assert isinstance(processor, TextProcessor)
