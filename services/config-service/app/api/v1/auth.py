"""Authentication endpoints."""

from typing import Annotated

from fastapi import APIRouter, Depends, Header, status
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.core.security import extract_bearer_token
from app.db.mongodb import get_db
from app.schemas.auth import (
    RegisterRequest,
    LoginRequest,
    RefreshRequest,
    LogoutRequest,
    TokenResponse,
    MessageResponse,
)
from app.services.auth_service import AuthService

router = APIRouter(prefix="/auth", tags=["authentication"])


@router.post(
    "/register",
    response_model=TokenResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register new user",
)
async def register(
    data: RegisterRequest,
    db: AsyncIOMotorDatabase = Depends(get_db),
) -> TokenResponse:
    """
    Register a new user account.

    Returns access and refresh tokens upon successful registration.
    """
    service = AuthService(db)
    return await service.register(data)


@router.post(
    "/login",
    response_model=TokenResponse,
    summary="User login",
)
async def login(
    data: LoginRequest,
    db: AsyncIOMotorDatabase = Depends(get_db),
) -> TokenResponse:
    """
    Authenticate user with email and password.

    Returns access and refresh tokens upon successful authentication.
    """
    service = AuthService(db)
    return await service.login(data)


@router.post(
    "/refresh",
    response_model=TokenResponse,
    summary="Refresh access token",
)
async def refresh(
    data: RefreshRequest,
    db: AsyncIOMotorDatabase = Depends(get_db),
) -> TokenResponse:
    """
    Refresh access token using a valid refresh token.
    """
    service = AuthService(db)
    return await service.refresh(data.refresh_token)


@router.post(
    "/logout",
    response_model=MessageResponse,
    summary="User logout",
)
async def logout(
    data: LogoutRequest | None = None,
    authorization: Annotated[str | None, Header()] = None,
    db: AsyncIOMotorDatabase = Depends(get_db),
) -> MessageResponse:
    """
    Logout user and revoke the current tokens.
    """
    service = AuthService(db)
    await service.logout(
        access_token=extract_bearer_token(authorization),
        refresh_token=data.refresh_token if data else None,
    )
    return MessageResponse(message="Successfully logged out")
