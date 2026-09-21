"""Security utilities for authentication."""

from datetime import datetime, timedelta, timezone
from typing import Optional
from uuid import uuid4

import bcrypt
from jose import jwt
from rag_config_common.auth.jwt_utils import (
    decode_token as shared_decode_token,
)
from rag_config_common.auth.jwt_utils import (
    extract_bearer_token,
    get_token_jti,
    get_token_ttl_seconds,
)

from app.core.settings import settings

# Re-exported from rag_config_common so the rest of this service imports auth
# helpers from one stable local path. Nothing in this module uses them
# directly, so __all__ is what tells ruff (and readers) they are public.
__all__ = [
    "create_access_token",
    "create_refresh_token",
    "decode_token",
    "extract_bearer_token",
    "get_password_hash",
    "get_token_jti",
    "get_token_ttl_seconds",
    "verify_password",
]


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against its hash."""
    password_bytes = plain_password.encode("utf-8")
    hashed_bytes = hashed_password.encode("utf-8")
    return bcrypt.checkpw(password_bytes, hashed_bytes)


def get_password_hash(password: str) -> str:
    """Generate password hash."""
    password_bytes = password.encode("utf-8")
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(password_bytes, salt)
    return hashed.decode("utf-8")


def create_access_token(
    subject: str,
    expires_delta: Optional[timedelta] = None,
) -> str:
    """Create JWT access token."""
    now = datetime.now(timezone.utc)
    expire = now + (
        expires_delta or timedelta(minutes=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    to_encode = {
        "exp": expire,
        "sub": subject,
        "type": "access",
        "iat": now,
        "jti": str(uuid4()),
    }
    return jwt.encode(
        to_encode,
        settings.JWT_SECRET_KEY,
        algorithm=settings.JWT_ALGORITHM,
    )


def create_refresh_token(
    subject: str,
    expires_delta: Optional[timedelta] = None,
) -> str:
    """Create JWT refresh token."""
    now = datetime.now(timezone.utc)
    expire = now + (
        expires_delta or timedelta(days=settings.JWT_REFRESH_TOKEN_EXPIRE_DAYS)
    )
    to_encode = {
        "exp": expire,
        "sub": subject,
        "type": "refresh",
        "iat": now,
        "jti": str(uuid4()),
    }
    return jwt.encode(
        to_encode,
        settings.JWT_SECRET_KEY,
        algorithm=settings.JWT_ALGORITHM,
    )


def decode_token(token: str) -> Optional[dict]:
    """Decode and validate JWT token."""
    return shared_decode_token(
        token,
        settings.JWT_SECRET_KEY,
        [settings.JWT_ALGORITHM],
    )
