"""Authentication service with business logic."""

from motor.motor_asyncio import AsyncIOMotorDatabase

from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    get_password_hash,
    get_token_jti,
    get_token_ttl_seconds,
    verify_password,
)
from app.core.audit import AuditLogger
from app.core.token_blacklist import token_blacklist
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
        self.audit_logger = AuditLogger(db)

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
        await self.audit_logger.log(
            user_id=user_id,
            action="user.create",
            resource_type="user",
            resource_id=user_id,
            details={"email": data.email},
        )

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

        token_jti = get_token_jti(payload)
        if not token_jti:
            raise UnauthorizedException("Invalid token payload")

        if await token_blacklist.is_blacklisted(token_jti):
            raise UnauthorizedException("Refresh token has been revoked")

        user_id = payload.get("sub")
        if not user_id:
            raise UnauthorizedException("Invalid token payload")

        # Verify user still exists and is active
        user = await self.user_repo.find_by_id(user_id)
        if not user or not user.get("is_active", False):
            raise UnauthorizedException("User not found or deactivated")

        await token_blacklist.blacklist_token(
            token_jti,
            get_token_ttl_seconds(payload),
        )

        return self._create_tokens(user_id)

    async def logout(
        self,
        access_token: str | None = None,
        refresh_token: str | None = None,
    ) -> None:
        """Blacklist access and refresh tokens until they expire."""
        await self._revoke_token(access_token, expected_type="access")
        await self._revoke_token(refresh_token, expected_type="refresh")

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

    async def _revoke_token(
        self,
        token: str | None,
        expected_type: str,
    ) -> None:
        """Blacklist a token when it is valid and matches the expected type."""
        if not token:
            return

        payload = decode_token(token)
        if not payload or payload.get("type") != expected_type:
            return

        token_jti = get_token_jti(payload)
        if not token_jti:
            return

        await token_blacklist.blacklist_token(
            token_jti,
            get_token_ttl_seconds(payload),
        )
