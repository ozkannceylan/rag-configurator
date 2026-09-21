"""Tests for ingestion task and utilities."""

import os
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from app.tasks.utils import (
    SUPPORTED_EXTENSIONS,
    ProgressTracker,
    compute_content_hash,
    compute_file_hash,
    format_file_size,
    get_all_supported_extensions,
    get_file_metadata,
    get_folder_path,
    get_processor_type,
    get_relative_path,
    is_supported_file,
    scan_directory,
)

# Import IngestionPipeline only if Celery is available
try:
    from app.tasks.ingestion_task import IngestionPipeline, compute_retry_countdown

    CELERY_AVAILABLE = True
except ImportError:
    CELERY_AVAILABLE = False
    IngestionPipeline = None
    compute_retry_countdown = None


class TestSupportedExtensions:
    """Tests for file extension helpers."""

    def test_get_all_supported_extensions(self):
        """Test getting all supported extensions."""
        extensions = get_all_supported_extensions()

        assert ".txt" in extensions
        assert ".pdf" in extensions
        assert ".docx" in extensions
        assert ".png" in extensions

    def test_is_supported_file_true(self):
        """Test supported file detection."""
        assert is_supported_file("document.pdf") is True
        assert is_supported_file("notes.txt") is True
        assert is_supported_file("report.docx") is True
        assert is_supported_file("image.png") is True

    def test_is_supported_file_false(self):
        """Test unsupported file detection."""
        assert is_supported_file("video.mp4") is False
        assert is_supported_file("archive.zip") is False
        assert is_supported_file("binary.exe") is False

    def test_is_supported_file_case_insensitive(self):
        """Test case insensitive extension matching."""
        assert is_supported_file("document.PDF") is True
        assert is_supported_file("image.PNG") is True
        assert is_supported_file("notes.TXT") is True

    def test_get_processor_type(self):
        """Test getting processor type by extension."""
        assert get_processor_type("doc.pdf") == "pdf"
        assert get_processor_type("doc.txt") == "text"
        assert get_processor_type("doc.docx") == "docx"
        assert get_processor_type("img.png") == "image"
        assert get_processor_type("unknown.xyz") is None


class TestFileHashing:
    """Tests for file hashing functions."""

    def test_compute_content_hash(self):
        """Test computing content hash."""
        hash1 = compute_content_hash("Hello World")
        hash2 = compute_content_hash("Hello World")
        hash3 = compute_content_hash("Different Content")

        assert hash1 == hash2
        assert hash1 != hash3
        assert len(hash1) == 32  # MD5 hex length

    def test_compute_file_hash(self):
        """Test computing file hash."""
        with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".txt") as f:
            f.write("Test content for hashing")
            temp_path = f.name

        try:
            hash1 = compute_file_hash(temp_path)
            hash2 = compute_file_hash(temp_path)

            assert hash1 == hash2
            assert len(hash1) == 32
        finally:
            os.unlink(temp_path)

    def test_compute_file_hash_nonexistent(self):
        """Test hashing nonexistent file returns empty string."""
        hash_value = compute_file_hash("/nonexistent/file.txt")
        assert hash_value == ""


class TestScanDirectory:
    """Tests for directory scanning."""

    def test_scan_directory_basic(self, workspace_temp_directory: Path):
        """Test basic directory scanning."""
        # Create test files
        (workspace_temp_directory / "doc1.txt").touch()
        (workspace_temp_directory / "doc2.pdf").touch()
        (workspace_temp_directory / "skip.xyz").touch()

        files = scan_directory(str(workspace_temp_directory), recursive=False)

        assert len(files) == 2
        assert any("doc1.txt" in f for f in files)
        assert any("doc2.pdf" in f for f in files)
        assert not any("skip.xyz" in f for f in files)

    def test_scan_directory_recursive(self, workspace_temp_directory: Path):
        """Test recursive directory scanning."""
        subdir = workspace_temp_directory / "subdir"
        subdir.mkdir()
        (workspace_temp_directory / "root.txt").touch()
        (subdir / "nested.txt").touch()

        files = scan_directory(str(workspace_temp_directory), recursive=True)

        assert len(files) == 2
        assert any("root.txt" in f for f in files)
        assert any("nested.txt" in f for f in files)

    def test_scan_directory_nonrecursive(self, workspace_temp_directory: Path):
        """Test non-recursive directory scanning."""
        subdir = workspace_temp_directory / "subdir"
        subdir.mkdir()
        (workspace_temp_directory / "root.txt").touch()
        (subdir / "nested.txt").touch()

        files = scan_directory(str(workspace_temp_directory), recursive=False)

        assert len(files) == 1
        assert any("root.txt" in f for f in files)

    def test_scan_directory_with_extensions(self, workspace_temp_directory: Path):
        """Test scanning with specific extensions."""
        (workspace_temp_directory / "doc.txt").touch()
        (workspace_temp_directory / "doc.pdf").touch()
        (workspace_temp_directory / "doc.docx").touch()

        files = scan_directory(
            str(workspace_temp_directory),
            recursive=False,
            include_extensions=[".txt", ".pdf"],
        )

        assert len(files) == 2
        assert not any("docx" in f for f in files)

    def test_scan_directory_nonexistent(self):
        """Test scanning nonexistent directory."""
        files = scan_directory("/nonexistent/directory")
        assert files == []

    def test_scan_directory_exclude_patterns(self, workspace_temp_directory: Path):
        """Test scanning with exclude patterns."""
        (workspace_temp_directory / "include.txt").touch()
        (workspace_temp_directory / "exclude_this.txt").touch()

        files = scan_directory(
            str(workspace_temp_directory),
            recursive=False,
            exclude_patterns=["exclude"],
        )

        assert len(files) == 1
        assert any("include.txt" in f for f in files)


class TestPathHelpers:
    """Tests for path helper functions."""

    def test_get_relative_path(self):
        """Test getting relative path."""
        result = get_relative_path("/base/subdir/file.txt", "/base")
        assert result == "subdir/file.txt" or result == "subdir\\file.txt"

    def test_get_relative_path_same_dir(self):
        """Test relative path in same directory."""
        result = get_relative_path("/base/file.txt", "/base")
        assert result == "file.txt"

    def test_get_folder_path(self):
        """Test getting folder path."""
        result = get_folder_path("/base/subdir/file.txt", "/base")
        assert result == "subdir" or result == "subdir"

    def test_format_file_size(self):
        """Test file size formatting."""
        assert "B" in format_file_size(100)
        assert "KB" in format_file_size(1024)
        assert "MB" in format_file_size(1024 * 1024)
        assert "GB" in format_file_size(1024 * 1024 * 1024)


class TestGetFileMetadata:
    """Tests for file metadata extraction."""

    def test_get_file_metadata(self):
        """Test getting file metadata."""
        with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".txt") as f:
            f.write("Test content")
            temp_path = f.name

        try:
            metadata = get_file_metadata(temp_path)

            assert metadata["file_type"] == ".txt"
            assert metadata["file_size_bytes"] > 0
            assert "file_name" in metadata
            assert "modified_at" in metadata
        finally:
            os.unlink(temp_path)

    def test_get_file_metadata_nonexistent(self):
        """Test metadata for nonexistent file."""
        metadata = get_file_metadata("/nonexistent/file.txt")

        assert metadata["file_name"] == "file.txt"
        assert metadata["file_type"] == ".txt"
        assert "file_size_bytes" not in metadata


class TestProgressTracker:
    """Tests for ProgressTracker."""

    def test_create_tracker(self):
        """Test creating a progress tracker."""
        tracker = ProgressTracker(
            total_files=10,
            ingestion_id="ing-123",
        )

        assert tracker.total_files == 10
        assert tracker.processed_files == 0
        assert tracker.progress_percent == 0.0

    def test_file_processed(self):
        """Test tracking processed files."""
        tracker = ProgressTracker(total_files=10, ingestion_id="ing-123")

        tracker.file_processed("file1.txt", chunks_created=5)
        tracker.file_processed("file2.txt", chunks_created=3)

        assert tracker.processed_files == 2
        assert tracker.total_chunks == 8
        assert tracker.progress_percent == 20.0

    def test_file_failed(self):
        """Test tracking failed files."""
        tracker = ProgressTracker(total_files=10, ingestion_id="ing-123")

        tracker.file_failed("file1.txt", "Parse error")

        assert tracker.failed_files == 1
        assert len(tracker.errors) == 1
        assert tracker.errors[0]["error"] == "Parse error"

    def test_set_step(self):
        """Test setting current step."""
        tracker = ProgressTracker(total_files=10, ingestion_id="ing-123")

        tracker.set_step("Processing files")
        assert tracker.current_step == "Processing files"

        tracker.set_step("Generating embeddings")
        assert tracker.current_step == "Generating embeddings"
        assert "Processing files" in tracker.steps_completed

    def test_add_graph_stats(self):
        """Test adding graph statistics."""
        tracker = ProgressTracker(total_files=10, ingestion_id="ing-123")

        tracker.add_graph_stats(nodes=5, edges=3)
        tracker.add_graph_stats(nodes=2, edges=1)

        assert tracker.graph_nodes == 7
        assert tracker.graph_edges == 4

    def test_get_meta(self):
        """Test getting progress metadata."""
        tracker = ProgressTracker(total_files=10, ingestion_id="ing-123")
        tracker.file_processed("file1.txt", chunks_created=5)

        meta = tracker.get_meta()

        assert meta["ingestion_id"] == "ing-123"
        assert meta["total_files"] == 10
        assert meta["processed_files"] == 1
        assert meta["progress"] == 10.0

    def test_get_final_stats(self):
        """Test getting final statistics."""
        tracker = ProgressTracker(total_files=10, ingestion_id="ing-123")
        tracker.file_processed("file1.txt", chunks_created=5, embeddings_created=5)

        stats = tracker.get_final_stats()

        assert stats["total_files"] == 10
        assert stats["processed_files"] == 1
        assert stats["total_chunks"] == 5
        assert "processing_time_seconds" in stats
        assert "started_at" in stats
        assert "completed_at" in stats

    def test_progress_with_celery_task(self):
        """Test progress updates with Celery task."""
        mock_task = MagicMock()
        tracker = ProgressTracker(
            total_files=10,
            ingestion_id="ing-123",
            celery_task=mock_task,
        )

        tracker.file_processed("file1.txt")

        mock_task.update_state.assert_called()


@pytest.mark.skipif(not CELERY_AVAILABLE, reason="Celery not installed")
class TestRetryBackoff:
    """Tests for Celery retry backoff logic."""

    def test_compute_retry_countdown_uses_exponential_backoff(self):
        """Test retry countdown grows exponentially with jitter."""
        with patch("app.tasks.ingestion_task.random.randint", return_value=7):
            assert compute_retry_countdown(0) == 67
            assert compute_retry_countdown(1) == 127
            assert compute_retry_countdown(2) == 247


@pytest.mark.skipif(not CELERY_AVAILABLE, reason="Celery not installed")
class TestIngestionPipeline:
    """Tests for IngestionPipeline."""

    def test_create_pipeline(self):
        """Test creating an ingestion pipeline."""
        pipeline = IngestionPipeline(
            config_id="config-123",
            user_id="user-456",
            ingestion_id="ing-789",
        )

        assert pipeline.config_id == "config-123"
        assert pipeline.user_id == "user-456"
        assert pipeline.ingestion_id == "ing-789"

    def test_create_pipeline_with_celery_task(self):
        """Test creating pipeline with Celery task."""
        mock_task = MagicMock()
        pipeline = IngestionPipeline(
            config_id="config-123",
            user_id="user-456",
            ingestion_id="ing-789",
            celery_task=mock_task,
        )

        assert pipeline.celery_task == mock_task


class TestSupportedExtensionsMapping:
    """Tests for SUPPORTED_EXTENSIONS constant."""

    def test_text_extensions(self):
        """Test text processor extensions."""
        assert ".txt" in SUPPORTED_EXTENSIONS["text"]
        assert ".md" in SUPPORTED_EXTENSIONS["text"]

    def test_pdf_extensions(self):
        """Test PDF processor extensions."""
        assert ".pdf" in SUPPORTED_EXTENSIONS["pdf"]

    def test_docx_extensions(self):
        """Test DOCX processor extensions."""
        assert ".docx" in SUPPORTED_EXTENSIONS["docx"]
        assert ".doc" in SUPPORTED_EXTENSIONS["docx"]

    def test_image_extensions(self):
        """Test image processor extensions."""
        assert ".png" in SUPPORTED_EXTENSIONS["image"]
        assert ".jpg" in SUPPORTED_EXTENSIONS["image"]
        assert ".jpeg" in SUPPORTED_EXTENSIONS["image"]

    def test_excel_extensions(self):
        """Test Excel processor extensions."""
        assert ".xlsx" in SUPPORTED_EXTENSIONS["excel"]
        assert ".csv" in SUPPORTED_EXTENSIONS["excel"]
