"""Tests for authentication endpoints."""

import pytest


@pytest.mark.asyncio
async def test_register_success(client, test_user_data):
    """Test successful user registration."""
    response = await client.post("/api/v1/auth/register", json=test_user_data)

    assert response.status_code == 201
    data = response.json()
    assert "access_token" in data
    assert "refresh_token" in data
    assert data["token_type"] == "bearer"


@pytest.mark.asyncio
async def test_register_duplicate_email(client, test_user_data):
    """Test registration with duplicate email."""
    # First registration
    await client.post("/api/v1/auth/register", json=test_user_data)

    # Second registration with same email
    response = await client.post("/api/v1/auth/register", json=test_user_data)

    assert response.status_code == 409


@pytest.mark.asyncio
async def test_login_success(client, test_user_data):
    """Test successful login."""
    # Register first
    await client.post("/api/v1/auth/register", json=test_user_data)

    # Login
    login_data = {
        "email": test_user_data["email"],
        "password": test_user_data["password"],
    }
    response = await client.post("/api/v1/auth/login", json=login_data)

    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data


@pytest.mark.asyncio
async def test_login_invalid_password(client, test_user_data):
    """Test login with invalid password."""
    # Register first
    await client.post("/api/v1/auth/register", json=test_user_data)

    # Login with wrong password
    login_data = {
        "email": test_user_data["email"],
        "password": "wrongpassword",
    }
    response = await client.post("/api/v1/auth/login", json=login_data)

    assert response.status_code == 401


@pytest.mark.asyncio
async def test_refresh_token(client, test_user_data):
    """Test token refresh."""
    # Register and get tokens
    response = await client.post("/api/v1/auth/register", json=test_user_data)
    refresh_token = response.json()["refresh_token"]

    # Refresh
    response = await client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": refresh_token},
    )

    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data


@pytest.mark.asyncio
async def test_refresh_token_cannot_be_reused(client, test_user_data):
    """Test a refresh token is revoked once it is exchanged."""
    response = await client.post("/api/v1/auth/register", json=test_user_data)
    refresh_token = response.json()["refresh_token"]

    first_refresh = await client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": refresh_token},
    )
    assert first_refresh.status_code == 200

    second_refresh = await client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": refresh_token},
    )
    assert second_refresh.status_code == 401


@pytest.mark.asyncio
async def test_logout_revokes_refresh_token(client, test_user_data):
    """Test logout blacklists the submitted refresh token."""
    response = await client.post("/api/v1/auth/register", json=test_user_data)
    tokens = response.json()

    logout_response = await client.post(
        "/api/v1/auth/logout",
        headers={"Authorization": f"Bearer {tokens['access_token']}"},
        json={"refresh_token": tokens["refresh_token"]},
    )
    assert logout_response.status_code == 200

    refresh_response = await client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": tokens["refresh_token"]},
    )
    assert refresh_response.status_code == 401
