"""E2E tests for authentication flow."""

import time
from datetime import datetime

import httpx
import pytest

from helpers import get_data

BASE_URL = "http://localhost:8000"


async def test_register_user(client: httpx.AsyncClient):
    """Test user registration."""
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    test_user = {
        "email": f"auth_test_{timestamp}@example.com",
        "password": "TestPassword123!",
        "name": f"Auth Test User {timestamp}",
    }

    response = await client.post("/api/v1/auth/register", json=test_user)
    assert response.status_code == 201
    data = get_data(response)

    assert "access_token" in data
    assert "refresh_token" in data
    assert data["token_type"] == "bearer"

    # Cleanup
    headers = {"Authorization": f"Bearer {data['access_token']}"}
    await client.post("/api/v1/auth/logout", headers=headers)


async def test_login_user(client: httpx.AsyncClient):
    """Test user login with registered user."""
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    test_user = {
        "email": f"login_test_{timestamp}@example.com",
        "password": "TestPassword123!",
        "name": f"Login Test User {timestamp}",
    }

    # Register first
    reg_response = await client.post("/api/v1/auth/register", json=test_user)
    assert reg_response.status_code == 201

    # Now login
    response = await client.post("/api/v1/auth/login", json={
        "email": test_user["email"],
        "password": test_user["password"],
    })
    assert response.status_code == 200
    data = get_data(response)

    assert "access_token" in data
    assert "refresh_token" in data
    assert data["token_type"] == "bearer"

    # Cleanup
    headers = {"Authorization": f"Bearer {data['access_token']}"}
    await client.post("/api/v1/auth/logout", headers=headers)


async def test_login_invalid_credentials(client: httpx.AsyncClient):
    """Test login with invalid credentials fails."""
    response = await client.post("/api/v1/auth/login", json={
        "email": "nonexistent@example.com",
        "password": "wrongpassword",
    })
    assert response.status_code in [401, 404]


async def test_access_protected_endpoint(client: httpx.AsyncClient):
    """Test accessing protected endpoint with valid token."""
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    test_user = {
        "email": f"protected_test_{timestamp}@example.com",
        "password": "TestPassword123!",
        "name": f"Protected Test User {timestamp}",
    }

    # Register and get token
    reg_response = await client.post("/api/v1/auth/register", json=test_user)
    assert reg_response.status_code == 201
    access_token = get_data(reg_response)["access_token"]

    # Access protected endpoint (user profile)
    headers = {"Authorization": f"Bearer {access_token}"}
    response = await client.get("/api/v1/users/me", headers=headers)
    assert response.status_code == 200
    data = get_data(response)
    assert data["email"] == test_user["email"]
    assert data["name"] == test_user["name"]

    # Cleanup
    await client.post("/api/v1/auth/logout", headers=headers)


async def test_access_protected_without_token(client: httpx.AsyncClient):
    """Test accessing protected endpoint without token fails."""
    response = await client.get("/api/v1/users/me")
    assert response.status_code == 401


async def test_refresh_token(client: httpx.AsyncClient):
    """Test token refresh flow."""
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    test_user = {
        "email": f"refresh_test_{timestamp}@example.com",
        "password": "TestPassword123!",
        "name": f"Refresh Test User {timestamp}",
    }

    # Register and get tokens
    reg_response = await client.post("/api/v1/auth/register", json=test_user)
    assert reg_response.status_code == 201
    data = get_data(reg_response)
    refresh_token = data["refresh_token"]
    old_access_token = data["access_token"]

    # Wait a moment to ensure different token
    time.sleep(0.1)

    # Refresh token
    response = await client.post("/api/v1/auth/refresh", json={
        "refresh_token": refresh_token,
    })
    assert response.status_code == 200
    new_data = get_data(response)

    assert "access_token" in new_data
    assert "refresh_token" in new_data
    # New access token should be different from old one
    assert new_data["access_token"] != old_access_token

    # Cleanup
    headers = {"Authorization": f"Bearer {new_data['access_token']}"}
    await client.post("/api/v1/auth/logout", headers=headers)


async def test_logout(client: httpx.AsyncClient):
    """Test logout endpoint."""
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    test_user = {
        "email": f"logout_test_{timestamp}@example.com",
        "password": "TestPassword123!",
        "name": f"Logout Test User {timestamp}",
    }

    # Register and get token
    reg_response = await client.post("/api/v1/auth/register", json=test_user)
    assert reg_response.status_code == 201
    access_token = get_data(reg_response)["access_token"]

    # Logout
    headers = {"Authorization": f"Bearer {access_token}"}
    response = await client.post("/api/v1/auth/logout", headers=headers)
    assert response.status_code == 200
    data = get_data(response)
    assert "message" in data


async def test_full_auth_flow(client: httpx.AsyncClient):
    """Test complete authentication flow."""
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    test_user = {
        "email": f"full_flow_{timestamp}@example.com",
        "password": "TestPassword123!",
        "name": f"Full Flow Test User {timestamp}",
    }

    # 1. Register
    reg_response = await client.post("/api/v1/auth/register", json=test_user)
    assert reg_response.status_code == 201
    data = get_data(reg_response)
    access_token = data["access_token"]
    refresh_token = data["refresh_token"]

    # 2. Access protected endpoint
    headers = {"Authorization": f"Bearer {access_token}"}
    me_response = await client.get("/api/v1/users/me", headers=headers)
    assert me_response.status_code == 200

    # 3. Refresh token
    refresh_response = await client.post("/api/v1/auth/refresh", json={
        "refresh_token": refresh_token,
    })
    assert refresh_response.status_code == 200
    new_access_token = get_data(refresh_response)["access_token"]

    # 4. Access with new token
    new_headers = {"Authorization": f"Bearer {new_access_token}"}
    me2_response = await client.get("/api/v1/users/me", headers=new_headers)
    assert me2_response.status_code == 200

    # 5. Logout
    logout_response = await client.post("/api/v1/auth/logout", headers=new_headers)
    assert logout_response.status_code == 200
