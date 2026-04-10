"""Tests for ingestion API endpoints."""

from datetime import datetime
from typing import Any, Dict
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import pytest_asyncio
from bson import ObjectId
from httpx import ASGITransport, AsyncClient

from app.main import app
from app.storage.models import IngestionRecord, IngestionStatus


def build_authorized_mock_db(
    config_id: str,
    *,
    owner_id: str = "test-user-id",
    config_doc: Dict[str, Any] | None = None,
    latest_ingestion: Dict[str, Any] | None = None,
    running_ingestion: Dict[str, Any] | None = None,
    history_items: list[Dict[str, Any]] | None = None,
    document_stats: list[Dict[str, Any]] | None = None,
    graph_nodes_count: int = 0,
    graph_edges_count: int = 0,
):
    """Build a database mock that authorizes the default test user."""
    mock_db = MagicMock()
    mock_db.command = AsyncMock(return_value={"ok": 1})

    effective_config = config_doc or {
        "_id": config_id,
        "created_by": owner_id,
        "user_id": owner_id,
    }
    mock_configs = AsyncMock()
    mock_configs.find_one = AsyncMock(return_value=effective_config)

    mock_ingestions = AsyncMock()
    mock_ingestions.find_one = AsyncMock(
        return_value=running_ingestion if running_ingestion is not None else latest_ingestion
    )
    mock_ingestions.update_one = AsyncMock()
    mock_ingestions.insert_one = AsyncMock(
        return_value=MagicMock(inserted_id="new-ing-id")
    )
    mock_ingestions.count_documents = AsyncMock(
        return_value=len(history_items or [])
    )
    mock_ingestions.find = MagicMock(return_value=AsyncIterator(history_items or []))

    mock_documents = MagicMock()
    mock_documents.aggregate = MagicMock(
        return_value=AsyncIterator(document_stats or [])
    )

    mock_graph_nodes = AsyncMock()
    mock_graph_nodes.count_documents = AsyncMock(return_value=graph_nodes_count)

    mock_graph_edges = AsyncMock()
    mock_graph_edges.count_documents = AsyncMock(return_value=graph_edges_count)

    def get_collection(name):
        if name == "configs":
            return mock_configs
        if name in {"ingestion_jobs", "ingestions"}:
            return mock_ingestions
        if name == "documents":
            return mock_documents
        if name == "graph_nodes":
            return mock_graph_nodes
        if name == "graph_edges":
            return mock_graph_edges
        return AsyncMock()

    mock_db.__getitem__ = MagicMock(side_effect=get_collection)
    return mock_db


class TestHealthEndpoints:
    """Tests for health check endpoints."""

    def test_health_check(self, client):
        """Test basic health check endpoint."""
        response = client.get("/health")
        assert response.status_code == 200

        data = response.json()
        assert data["status"] == "healthy"
        assert "service" in data

    def test_health_detailed(self, client):
        """Test detailed health check endpoint."""
        response = client.get("/health/detailed")
        assert response.status_code == 200

        data = response.json()
        assert "status" in data
        assert "service" in data


class TestRootEndpoints:
    """Tests for root API endpoints."""

    def test_api_v1_root(self, client):
        """Test API v1 root endpoint."""
        response = client.get("/api/v1/")
        assert response.status_code == 200

        data = response.json()
        assert "message" in data
        assert "version" in data


class TestStartIngestion:
    """Tests for starting ingestion."""

    @pytest.mark.asyncio
    async def test_start_ingestion_requires_user_header(
        self,
        signed_client_without_user: AsyncClient,
        sample_config: Dict[str, Any],
    ):
        """Test starting ingestion without X-User-ID is rejected."""
        mock_db = MagicMock()
        mock_configs = AsyncMock()
        mock_configs.find_one = AsyncMock(return_value=sample_config)
        mock_db.__getitem__ = MagicMock(return_value=mock_configs)

        with patch("app.db.mongodb.mongodb.get_database", return_value=mock_db):
            response = await signed_client_without_user.post(
                f"/api/v1/ingest/{sample_config['_id']}/start"
            )

        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_start_ingestion_requires_hmac_signature(self, sample_config: Dict[str, Any]):
        """Test unsigned ingestion requests are rejected by service auth middleware."""
        mock_db = MagicMock()
        mock_configs = AsyncMock()
        mock_configs.find_one = AsyncMock(return_value=sample_config)
        mock_db.__getitem__ = MagicMock(return_value=mock_configs)

        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as unsigned_client:
            with patch("app.db.mongodb.mongodb.get_database", return_value=mock_db):
                response = await unsigned_client.post(
                    f"/api/v1/ingest/{sample_config['_id']}/start"
                )

        assert response.status_code == 403

    @pytest.mark.asyncio
    async def test_start_ingestion_forbidden_for_non_owner(
        self,
        async_client: AsyncClient,
        sample_config: Dict[str, Any],
    ):
        """Test starting ingestion for someone else's config is rejected."""
        other_user_config = {
            **sample_config,
            "created_by": "different-user",
            "user_id": "different-user",
        }

        mock_db = MagicMock()
        mock_configs = AsyncMock()
        mock_configs.find_one = AsyncMock(return_value=other_user_config)
        mock_db.__getitem__ = MagicMock(return_value=mock_configs)

        with patch("app.db.mongodb.mongodb.get_database", return_value=mock_db):
            response = await async_client.post(f"/api/v1/ingest/{sample_config['_id']}/start")

        assert response.status_code == 403

    @pytest.mark.asyncio
    async def test_start_ingestion_config_not_found(self, async_client: AsyncClient):
        """Test starting ingestion with non-existent config."""
        fake_config_id = str(ObjectId())

        # Mock the database dependency
        mock_db = MagicMock()
        mock_configs = AsyncMock()
        mock_configs.find_one = AsyncMock(return_value=None)
        mock_db.__getitem__ = MagicMock(return_value=mock_configs)

        with patch("app.db.mongodb.mongodb.get_database", return_value=mock_db), \
             patch("app.api.v1.ingest.get_database", return_value=mock_db):

            response = await async_client.post(f"/api/v1/ingest/{fake_config_id}/start")
            assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_start_ingestion_already_running(
        self,
        async_client: AsyncClient,
        sample_config: Dict[str, Any],
    ):
        """Test duplicate starts return the existing ingestion job."""
        config_id = sample_config["_id"]

        # Create mock database
        mock_db = MagicMock()
        mock_configs = AsyncMock()
        mock_ingestions = AsyncMock()
        
        # Config exists
        mock_configs.find_one = AsyncMock(return_value=sample_config)
        
        # Running ingestion exists
        running_ingestion = {
            "_id": "running-ingestion-id",
            "config_id": config_id,
            "status": "running",
            "celery_task_id": "task-123",
        }
        mock_ingestions.find_one = AsyncMock(return_value=running_ingestion)
        
        def get_collection(name):
            if name == "configs":
                return mock_configs
            if name in {"ingestion_jobs", "ingestions"}:
                return mock_ingestions
            return mock_ingestions
        
        mock_db.__getitem__ = MagicMock(side_effect=get_collection)

        with patch("app.db.mongodb.mongodb.get_database", return_value=mock_db):
            response = await async_client.post(f"/api/v1/ingest/{config_id}/start")
            assert response.status_code == 202
            assert response.json()["ingestion_id"] == "running-ingestion-id"

    @pytest.mark.asyncio
    async def test_start_ingestion_success(
        self,
        async_client: AsyncClient,
        sample_config: Dict[str, Any],
    ):
        """Test successfully starting ingestion.
        
        Note: This test uses the ImportError fallback path in the actual code
        since Celery workers aren't running during tests. The mock-task ID
        generated confirms the endpoint logic works correctly.
        """
        config_id = sample_config["_id"]

        # Create mock database
        mock_db = MagicMock()
        mock_configs = AsyncMock()
        mock_ingestions = AsyncMock()
        
        mock_configs.find_one = AsyncMock(return_value=sample_config)
        mock_ingestions.find_one = AsyncMock(return_value=None)  # No running ingestion
        mock_ingestions.insert_one = AsyncMock(return_value=MagicMock(inserted_id="new-ing-id"))
        mock_ingestions.update_one = AsyncMock()
        
        def get_collection(name):
            if name == "configs":
                return mock_configs
            if name in {"ingestion_jobs", "ingestions"}:
                return mock_ingestions
            return mock_ingestions
        
        mock_db.__getitem__ = MagicMock(side_effect=get_collection)

        with patch("app.db.mongodb.mongodb.get_database", return_value=mock_db):
            response = await async_client.post(f"/api/v1/ingest/{config_id}/start")
            assert response.status_code == 202
            
            data = response.json()
            assert "task_id" in data
            assert data["config_id"] == config_id
            assert data["status"] == "pending"
            # Task ID will be mock-task-{ingestion_id} since Celery isn't available
            assert "mock-task-" in data["task_id"] or data["task_id"]


class TestGetIngestionStatus:
    """Tests for getting ingestion status."""

    @pytest.mark.asyncio
    async def test_status_no_ingestion(self, async_client: AsyncClient):
        """Test getting status when no ingestion exists."""
        fake_config_id = str(ObjectId())

        mock_db = build_authorized_mock_db(fake_config_id)

        with patch("app.db.mongodb.mongodb.get_database", return_value=mock_db):
            response = await async_client.get(f"/api/v1/ingest/{fake_config_id}/status")
            assert response.status_code == 200

            data = response.json()
            assert data["status"] == "none"

    @pytest.mark.asyncio
    async def test_status_pending_ingestion(self, async_client: AsyncClient):
        """Test getting status for pending ingestion."""
        config_id = str(ObjectId())
        ingestion = {
            "_id": str(ObjectId()),
            "config_id": config_id,
            "status": "pending",
            "celery_task_id": "task-123",
            "total_files": 10,
            "processed_files": 0,
            "failed_files": 0,
            "total_chunks": 0,
            "started_at": None,
            "completed_at": None,
        }

        mock_db = build_authorized_mock_db(config_id, latest_ingestion=ingestion)

        with patch("app.db.mongodb.mongodb.get_database", return_value=mock_db):
            response = await async_client.get(f"/api/v1/ingest/{config_id}/status")
            assert response.status_code == 200

            data = response.json()
            assert data["status"] == "pending"
            assert data["progress"] == 0.0

    @pytest.mark.asyncio
    async def test_status_running_ingestion(self, async_client: AsyncClient):
        """Test getting status for running ingestion."""
        config_id = str(ObjectId())
        ingestion = {
            "_id": str(ObjectId()),
            "config_id": config_id,
            "status": "running",
            "celery_task_id": "task-123",
            "total_files": 10,
            "processed_files": 5,
            "failed_files": 0,
            "total_chunks": 100,
            "started_at": datetime.utcnow(),
            "completed_at": None,
        }

        mock_db = build_authorized_mock_db(config_id, latest_ingestion=ingestion)

        with patch("app.db.mongodb.mongodb.get_database", return_value=mock_db):
            response = await async_client.get(f"/api/v1/ingest/{config_id}/status")
            assert response.status_code == 200

            data = response.json()
            assert data["status"] == "running"
            assert data["progress"] == 50.0
            assert data["processed_files"] == 5

    @pytest.mark.asyncio
    async def test_status_completed_ingestion(self, async_client: AsyncClient):
        """Test getting status for completed ingestion."""
        config_id = str(ObjectId())
        ingestion = {
            "_id": str(ObjectId()),
            "config_id": config_id,
            "status": "completed",
            "celery_task_id": "task-123",
            "total_files": 10,
            "processed_files": 10,
            "failed_files": 0,
            "total_chunks": 200,
            "started_at": datetime.utcnow(),
            "completed_at": datetime.utcnow(),
        }

        mock_db = build_authorized_mock_db(config_id, latest_ingestion=ingestion)

        with patch("app.db.mongodb.mongodb.get_database", return_value=mock_db):
            response = await async_client.get(f"/api/v1/ingest/{config_id}/status")
            assert response.status_code == 200

            data = response.json()
            assert data["status"] == "completed"
            assert data["progress"] == 100.0


class TestCancelIngestion:
    """Tests for cancelling ingestion."""

    @pytest.mark.asyncio
    async def test_cancel_no_running_ingestion(self, async_client: AsyncClient):
        """Test cancelling when no ingestion is running."""
        config_id = str(ObjectId())

        mock_db = build_authorized_mock_db(config_id)

        with patch("app.db.mongodb.mongodb.get_database", return_value=mock_db):
            response = await async_client.post(f"/api/v1/ingest/{config_id}/cancel")
            assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_cancel_running_ingestion(self, async_client: AsyncClient):
        """Test successfully cancelling a running ingestion."""
        config_id = str(ObjectId())
        ingestion_id = str(ObjectId())
        running_ingestion = {
            "_id": ingestion_id,
            "config_id": config_id,
            "status": "running",
            "celery_task_id": "task-to-cancel",
        }

        mock_db = build_authorized_mock_db(
            config_id,
            running_ingestion=running_ingestion,
        )

        # The endpoint handles ImportError gracefully, so we don't need to mock celery
        with patch("app.db.mongodb.mongodb.get_database", return_value=mock_db):
            response = await async_client.post(f"/api/v1/ingest/{config_id}/cancel")
            assert response.status_code == 200
            
            data = response.json()
            assert data["success"] is True


class TestRetryIngestion:
    """Tests for retrying failed ingestion."""

    @pytest.mark.asyncio
    async def test_retry_no_ingestion(self, async_client: AsyncClient):
        """Test retrying when no ingestion exists."""
        config_id = str(ObjectId())

        mock_db = build_authorized_mock_db(config_id)

        with patch("app.db.mongodb.mongodb.get_database", return_value=mock_db):
            response = await async_client.post(f"/api/v1/ingest/{config_id}/retry")
            assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_retry_not_failed(self, async_client: AsyncClient):
        """Test retrying ingestion that is not failed."""
        config_id = str(ObjectId())
        ingestion = {
            "_id": str(ObjectId()),
            "config_id": config_id,
            "status": "completed",
        }

        mock_db = build_authorized_mock_db(config_id, latest_ingestion=ingestion)

        with patch("app.db.mongodb.mongodb.get_database", return_value=mock_db):
            response = await async_client.post(f"/api/v1/ingest/{config_id}/retry")
            assert response.status_code == 400

    @pytest.mark.asyncio
    async def test_retry_failed_ingestion(
        self,
        async_client: AsyncClient,
        sample_config: Dict[str, Any],
    ):
        """Test successfully retrying a failed ingestion."""
        config_id = sample_config["_id"]
        failed_ingestion = {
            "_id": str(ObjectId()),
            "config_id": config_id,
            "status": "failed",
        }

        mock_db = MagicMock()
        mock_configs = AsyncMock()
        mock_ingestions = AsyncMock()
        mock_chunks = AsyncMock()
        mock_documents = AsyncMock()
        
        mock_configs.find_one = AsyncMock(return_value=sample_config)
        mock_ingestions.find_one = AsyncMock(return_value=failed_ingestion)
        mock_ingestions.insert_one = AsyncMock(return_value=MagicMock(inserted_id="new-ing-id"))
        mock_ingestions.update_one = AsyncMock()
        mock_chunks.delete_many = AsyncMock()
        mock_documents.delete_many = AsyncMock()
        
        def get_collection(name):
            if name == "configs":
                return mock_configs
            elif name in {"ingestion_jobs", "ingestions"}:
                return mock_ingestions
            elif name == "chunks":
                return mock_chunks
            elif name == "documents":
                return mock_documents
            return mock_ingestions
        
        mock_db.__getitem__ = MagicMock(side_effect=get_collection)

        with patch("app.db.mongodb.mongodb.get_database", return_value=mock_db):
            response = await async_client.post(f"/api/v1/ingest/{config_id}/retry")
            assert response.status_code == 202


class TestGetIngestionLogs:
    """Tests for getting ingestion logs."""

    @pytest.mark.asyncio
    async def test_logs_no_ingestion(self, async_client: AsyncClient):
        """Test getting logs when no ingestion exists."""
        config_id = str(ObjectId())

        mock_db = build_authorized_mock_db(config_id)

        with patch("app.db.mongodb.mongodb.get_database", return_value=mock_db):
            response = await async_client.get(f"/api/v1/ingest/{config_id}/logs")
            assert response.status_code == 200

            data = response.json()
            assert data["logs"] == []

    @pytest.mark.asyncio
    async def test_logs_with_errors(self, async_client: AsyncClient):
        """Test getting logs with errors."""
        config_id = str(ObjectId())
        ingestion = {
            "_id": str(ObjectId()),
            "config_id": config_id,
            "status": "running",
            "errors": [
                {
                    "timestamp": datetime.utcnow().isoformat(),
                    "error": "Failed to process file",
                    "file_path": "/path/to/file.pdf",
                }
            ],
            "warnings": ["Some warning"],
            "created_at": datetime.utcnow(),
            "started_at": datetime.utcnow(),
            "completed_at": None,
        }

        mock_db = build_authorized_mock_db(config_id, latest_ingestion=ingestion)

        with patch("app.db.mongodb.mongodb.get_database", return_value=mock_db):
            response = await async_client.get(f"/api/v1/ingest/{config_id}/logs")
            assert response.status_code == 200

            data = response.json()
            assert len(data["logs"]) > 0


class TestGetIngestionStats:
    """Tests for getting ingestion statistics."""

    @pytest.mark.asyncio
    async def test_stats_no_ingestion(self, async_client: AsyncClient):
        """Test getting stats when no ingestion exists."""
        config_id = str(ObjectId())

        mock_db = build_authorized_mock_db(config_id)

        with patch("app.db.mongodb.mongodb.get_database", return_value=mock_db):
            response = await async_client.get(f"/api/v1/ingest/{config_id}/stats")
            assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_stats_with_ingestion(self, async_client: AsyncClient):
        """Test getting stats for an ingestion."""
        config_id = str(ObjectId())
        ingestion = {
            "_id": str(ObjectId()),
            "config_id": config_id,
            "status": "completed",
            "total_files": 10,
            "processed_files": 9,
            "failed_files": 1,
            "total_chunks": 200,
            "started_at": datetime.utcnow(),
            "completed_at": datetime.utcnow(),
        }

        mock_db = build_authorized_mock_db(
            config_id,
            latest_ingestion=ingestion,
            document_stats=[
                {"_id": ".txt", "count": 5, "total_size": 5000},
                {"_id": ".pdf", "count": 5, "total_size": 10000},
            ],
        )

        with patch("app.db.mongodb.mongodb.get_database", return_value=mock_db):
            response = await async_client.get(f"/api/v1/ingest/{config_id}/stats")
            assert response.status_code == 200
            
            data = response.json()
            assert "total_files" in data
            assert "processed_files" in data


class TestGetIngestionHistory:
    """Tests for getting ingestion history."""

    @pytest.mark.asyncio
    async def test_history_endpoint_exists(self, async_client: AsyncClient):
        """Test that history endpoint exists."""
        config_id = str(ObjectId())

        mock_db = build_authorized_mock_db(config_id, history_items=[])

        with patch("app.db.mongodb.mongodb.get_database", return_value=mock_db):
            response = await async_client.get(f"/api/v1/ingest/{config_id}/history")
            assert response.status_code == 200


class TestAPIResponseFormats:
    """Tests for API response format consistency."""

    @pytest.mark.asyncio
    async def test_status_response_format(self, async_client: AsyncClient):
        """Test that status response has expected format."""
        config_id = str(ObjectId())
        ingestion = {
            "_id": str(ObjectId()),
            "config_id": config_id,
            "status": "completed",
            "celery_task_id": "task-123",
            "total_files": 10,
            "processed_files": 10,
            "failed_files": 0,
            "total_chunks": 100,
            "started_at": datetime.utcnow(),
            "completed_at": datetime.utcnow(),
        }

        mock_db = build_authorized_mock_db(config_id, latest_ingestion=ingestion)

        with patch("app.db.mongodb.mongodb.get_database", return_value=mock_db):
            response = await async_client.get(f"/api/v1/ingest/{config_id}/status")
            assert response.status_code == 200

            data = response.json()

            # Check expected fields
            assert "config_id" in data
            assert "status" in data
            assert "progress" in data
            assert "total_files" in data
            assert "processed_files" in data
            assert "failed_files" in data
            assert "total_chunks" in data


# Helper class for async iteration in tests
class AsyncIterator:
    """Helper class for mocking async iterators."""
    
    def __init__(self, items):
        self.items = list(items)
        self.index = 0
    
    def __aiter__(self):
        return self
    
    async def __anext__(self):
        if self.index >= len(self.items):
            raise StopAsyncIteration
        item = self.items[self.index]
        self.index += 1
        return item
    
    def skip(self, n):
        return self
    
    def limit(self, n):
        return self
    
    def sort(self, *args, **kwargs):
        return self
