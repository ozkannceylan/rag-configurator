"""Authentication endpoints."""

from fastapi import APIRouter, Depends, status
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.db.mongodb import get_db
from app.schemas.auth import (
    RegisterRequest,
    LoginRequest,
    RefreshRequest,
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
async def logout() -> MessageResponse:
    """
    Logout user.

    Note: With JWT, actual token invalidation requires a token blacklist
    which is not implemented in this basic version. The client should
    discard the tokens.
    """
    return MessageResponse(message="Successfully logged out")
