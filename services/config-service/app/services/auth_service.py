"""Authentication service with business logic."""

from motor.motor_asyncio import AsyncIOMotorDatabase

from app.core.security import (
    verify_password,
    get_password_hash,
    create_access_token,
    create_refresh_token,
    decode_token,
)
from app.core.settings import settings
from app.core.exceptions import (
    UnauthorizedException,
    AlreadyExistsException,
)
from app.db.repositories.user_repo import UserRepository
from app.schemas.auth import RegisterRequest, LoginRequest, TokenResponse


class AuthService:
    """Service for authentication operations."""

    def __init__(self, db: AsyncIOMotorDatabase):
        self.user_repo = UserRepository(db)

    async def register(self, data: RegisterRequest) -> TokenResponse:
        """Register a new user."""
        # Check if user exists
        existing = await self.user_repo.find_by_email(data.email)
        if existing:
            raise AlreadyExistsException("User", "email", data.email)

        # Create user
        user_data = {
            "email": data.email,
            "name": data.name,
            "password_hash": get_password_hash(data.password),
        }
        user_id = await self.user_repo.create_user(user_data)

        # Generate tokens
        return self._create_tokens(user_id)

    async def login(self, data: LoginRequest) -> TokenResponse:
        """Authenticate user and return tokens."""
        user = await self.user_repo.find_by_email(data.email)

        if not user:
            raise UnauthorizedException("Invalid email or password")

        if not user.get("is_active", False):
            raise UnauthorizedException("Account is deactivated")

        if not verify_password(data.password, user["password_hash"]):
            raise UnauthorizedException("Invalid email or password")

        return self._create_tokens(str(user["_id"]))

    async def refresh(self, refresh_token: str) -> TokenResponse:
        """Refresh access token using refresh token."""
        payload = decode_token(refresh_token)

        if not payload:
            raise UnauthorizedException("Invalid refresh token")

        if payload.get("type") != "refresh":
            raise UnauthorizedException("Invalid token type")

        user_id = payload.get("sub")
        if not user_id:
            raise UnauthorizedException("Invalid token payload")

        # Verify user still exists and is active
        user = await self.user_repo.find_by_id(user_id)
        if not user or not user.get("is_active", False):
            raise UnauthorizedException("User not found or deactivated")

        return self._create_tokens(user_id)

    def _create_tokens(self, user_id: str) -> TokenResponse:
        """Create access and refresh tokens."""
        access_token = create_access_token(user_id)
        refresh_token = create_refresh_token(user_id)

        return TokenResponse(
            access_token=access_token,
            refresh_token=refresh_token,
            token_type="bearer",
            expires_in=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        )
