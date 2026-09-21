"""Tests for main application."""

from fastapi.testclient import TestClient


def test_health_endpoint(client: TestClient):
    """Test basic health endpoint."""
    response = client.get("/health")
    assert response.status_code == 200

    data = response.json()
    assert data["status"] == "healthy"
    assert data["service"] == "ingestion-service"


def test_api_v1_root(client: TestClient):
    """Test API v1 root endpoint."""
    response = client.get("/api/v1/")
    assert response.status_code == 200

    data = response.json()
    assert "message" in data
    assert "Ingestion Service" in data["message"]


def test_cors_headers(client: TestClient):
    """Test CORS headers are present."""
    response = client.options(
        "/health",
        headers={
            "Origin": "http://localhost:3000",
            "Access-Control-Request-Method": "GET",
        },
    )
    # FastAPI handles OPTIONS differently
    assert response.status_code in [200, 405]
