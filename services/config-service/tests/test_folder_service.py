"""Tests for folder scanning service (no MongoDB required)."""

import tempfile
from pathlib import Path

import pytest
from rag_config_common.models.enums import DataSourceType, DataType

from app.schemas.folder import FolderScanRequest
from app.services.folder_service import EXTENSION_MAP, MULTIMODAL_TYPES, FolderService


class TestFolderService:
    """Tests for FolderService."""

    @pytest.fixture
    def folder_service(self):
        """Create a folder service instance."""
        return FolderService()

    @pytest.fixture
    def temp_dir(self):
        """Create a temporary directory structure for testing."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create subdirectories
            docs_dir = Path(tmpdir) / "documents"
            images_dir = Path(tmpdir) / "images"
            nested_dir = Path(tmpdir) / "nested" / "deep"
            docs_dir.mkdir()
            images_dir.mkdir()
            nested_dir.mkdir(parents=True)

            # Create test files
            (docs_dir / "readme.txt").write_text("Hello")
            (docs_dir / "notes.md").write_text("# Notes")
            (docs_dir / "report.pdf").write_bytes(b"PDF content")
            (images_dir / "photo.png").write_bytes(b"PNG content")
            (images_dir / "diagram.jpg").write_bytes(b"JPG content")
            (nested_dir / "deep_file.txt").write_text("Deep")

            # Create a hidden file (should be ignored)
            (docs_dir / ".hidden").write_text("hidden")

            yield tmpdir

    def test_scan_valid_directory(self, folder_service, temp_dir):
        """Test scanning a valid directory."""
        request = FolderScanRequest(
            type=DataSourceType.LOCAL,
            base_path=temp_dir,
        )
        result = folder_service.scan(request)

        assert result.base_path == str(Path(temp_dir).absolute())
        assert len(result.folders) > 0

    def test_scan_detects_file_types(self, folder_service, temp_dir):
        """Test that scanning detects correct file types."""
        request = FolderScanRequest(
            type=DataSourceType.LOCAL,
            base_path=temp_dir,
        )
        result = folder_service.scan(request)

        # Find the documents folder
        docs_folder = next((f for f in result.folders if f.name == "documents"), None)
        assert docs_folder is not None

        detected = set(docs_folder.detected_types)
        assert DataType.TEXT in detected
        assert DataType.MARKDOWN in detected
        assert DataType.PDF in detected

    def test_scan_detects_images(self, folder_service, temp_dir):
        """Test that scanning detects image files."""
        request = FolderScanRequest(
            type=DataSourceType.LOCAL,
            base_path=temp_dir,
        )
        result = folder_service.scan(request)

        # Find the images folder
        images_folder = next((f for f in result.folders if f.name == "images"), None)
        assert images_folder is not None
        assert DataType.IMAGE in images_folder.detected_types

    def test_scan_has_multimodal_flag(self, folder_service, temp_dir):
        """Test that has_multimodal is set correctly."""
        request = FolderScanRequest(
            type=DataSourceType.LOCAL,
            base_path=temp_dir,
        )
        result = folder_service.scan(request)

        # Should have multimodal content (images and PDFs)
        assert result.has_multimodal is True

    def test_scan_nested_directories(self, folder_service, temp_dir):
        """Test scanning nested directories."""
        request = FolderScanRequest(
            type=DataSourceType.LOCAL,
            base_path=temp_dir,
        )
        result = folder_service.scan(request)

        # Find the nested folder
        nested_folder = next((f for f in result.folders if f.name == "nested"), None)
        assert nested_folder is not None
        assert len(nested_folder.children) > 0

    def test_scan_nonexistent_path_raises_error(self, folder_service):
        """Test that scanning nonexistent path raises ValueError."""
        request = FolderScanRequest(
            type=DataSourceType.LOCAL,
            base_path="/nonexistent/path/that/does/not/exist",
        )
        with pytest.raises(ValueError, match="does not exist"):
            folder_service.scan(request)

    def test_scan_file_instead_of_directory_raises_error(
        self, folder_service, temp_dir
    ):
        """Test that scanning a file instead of directory raises ValueError."""
        # Create a file to scan
        file_path = Path(temp_dir) / "test.txt"
        file_path.write_text("content")

        request = FolderScanRequest(
            type=DataSourceType.LOCAL,
            base_path=str(file_path),
        )
        with pytest.raises(ValueError, match="not a directory"):
            folder_service.scan(request)

    def test_scan_unsupported_source_type_raises_error(self, folder_service, temp_dir):
        """Test that unsupported source type raises NotImplementedError."""
        request = FolderScanRequest(
            type=DataSourceType.S3,
            base_path="s3://bucket/path",
        )
        with pytest.raises(NotImplementedError, match="not yet supported"):
            folder_service.scan(request)

    def test_scan_counts_files_correctly(self, folder_service, temp_dir):
        """Test that file counting is correct."""
        request = FolderScanRequest(
            type=DataSourceType.LOCAL,
            base_path=temp_dir,
        )
        result = folder_service.scan(request)

        # Find the documents folder (should have 3 files, not counting hidden)
        docs_folder = next((f for f in result.folders if f.name == "documents"), None)
        assert docs_folder is not None
        assert docs_folder.file_count == 3

    def test_scan_ignores_hidden_files(self, folder_service, temp_dir):
        """Test that hidden files are ignored."""
        request = FolderScanRequest(
            type=DataSourceType.LOCAL,
            base_path=temp_dir,
        )
        result = folder_service.scan(request)

        # Documents folder should only count visible files
        docs_folder = next((f for f in result.folders if f.name == "documents"), None)
        # We created 3 visible files + 1 hidden, count should be 3
        assert docs_folder.file_count == 3


class TestExtensionMapping:
    """Tests for file extension mapping."""

    def test_text_extensions(self):
        """Test text file extensions."""
        assert EXTENSION_MAP[".txt"] == DataType.TEXT

    def test_markdown_extensions(self):
        """Test markdown file extensions."""
        assert EXTENSION_MAP[".md"] == DataType.MARKDOWN
        assert EXTENSION_MAP[".markdown"] == DataType.MARKDOWN

    def test_pdf_extension(self):
        """Test PDF extension."""
        assert EXTENSION_MAP[".pdf"] == DataType.PDF

    def test_image_extensions(self):
        """Test image file extensions."""
        assert EXTENSION_MAP[".png"] == DataType.IMAGE
        assert EXTENSION_MAP[".jpg"] == DataType.IMAGE
        assert EXTENSION_MAP[".jpeg"] == DataType.IMAGE
        assert EXTENSION_MAP[".gif"] == DataType.IMAGE
        assert EXTENSION_MAP[".webp"] == DataType.IMAGE

    def test_document_extensions(self):
        """Test document file extensions."""
        assert EXTENSION_MAP[".docx"] == DataType.DOCX
        assert EXTENSION_MAP[".doc"] == DataType.DOCX
        assert EXTENSION_MAP[".xlsx"] == DataType.XLSX
        assert EXTENSION_MAP[".xls"] == DataType.XLSX
        assert EXTENSION_MAP[".csv"] == DataType.CSV


class TestMultimodalTypes:
    """Tests for multimodal type detection."""

    def test_image_is_multimodal(self):
        """Test that IMAGE is considered multimodal."""
        assert DataType.IMAGE in MULTIMODAL_TYPES

    def test_pdf_is_multimodal(self):
        """Test that PDF is considered multimodal."""
        assert DataType.PDF in MULTIMODAL_TYPES

    def test_text_is_not_multimodal(self):
        """Test that TEXT is not considered multimodal."""
        assert DataType.TEXT not in MULTIMODAL_TYPES

    def test_markdown_is_not_multimodal(self):
        """Test that MARKDOWN is not considered multimodal."""
        assert DataType.MARKDOWN not in MULTIMODAL_TYPES
