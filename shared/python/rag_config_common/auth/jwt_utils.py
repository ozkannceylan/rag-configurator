"""Shared JWT parsing helpers used across Python services."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional, Sequence

from jose import JWTError, jwt


def decode_token(
    token: str,
    secret_key: str,
    algorithms: Sequence[str],
) -> Optional[dict]:
    """Decode and validate a JWT, returning None on failure."""
    try:
        return jwt.decode(token, secret_key, algorithms=list(algorithms))
    except JWTError:
        return None


def verify_token_type(payload: Optional[dict], expected_type: str) -> bool:
    """Return True when a decoded JWT payload matches the expected type."""
    return bool(payload and payload.get("type") == expected_type)


def extract_bearer_token(authorization: Optional[str]) -> Optional[str]:
    """Extract a bearer token from an Authorization header."""
    if not authorization:
        return None

    parts = authorization.split()
    if len(parts) != 2 or parts[0].lower() != "bearer":
        return None

    return parts[1]


def get_token_subject(payload: Optional[dict]) -> Optional[str]:
    """Return the JWT subject from a token payload."""
    if not payload:
        return None
    return payload.get("sub")


def get_token_type(payload: Optional[dict]) -> Optional[str]:
    """Return the JWT type from a token payload."""
    if not payload:
        return None
    return payload.get("type")


def get_token_jti(payload: Optional[dict]) -> Optional[str]:
    """Return the JWT ID from a token payload."""
    if not payload:
        return None
    return payload.get("jti")


def get_token_ttl_seconds(
    payload: Optional[dict],
    now: Optional[datetime] = None,
) -> int:
    """Compute the remaining lifetime for a decoded token."""
    if not payload or "exp" not in payload:
        return 0

    expires_at = payload["exp"]
    if isinstance(expires_at, datetime):
        expiry = expires_at.astimezone(timezone.utc)
    else:
        expiry = datetime.fromtimestamp(expires_at, tz=timezone.utc)

    current_time = now or datetime.now(timezone.utc)
    remaining = int((expiry - current_time).total_seconds())
    return max(0, remaining)
