"""API dependencies for dependency injection."""

from typing import Annotated
from fastapi import Depends, Header
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.db.mongodb import get_db
from app.db.repositories.user_repo import UserRepository
from app.core.security import decode_token
from app.core.exceptions import UnauthorizedException
from app.schemas.user import UserResponse


async def get_current_user(
    authorization: Annotated[str | None, Header()] = None,
    db: AsyncIOMotorDatabase = Depends(get_db),
) -> UserResponse:
    """
    Dependency to get current authenticated user from JWT token.

    Extracts the Bearer token from Authorization header,
    validates it, and returns the user.
    """
    if not authorization:
        raise UnauthorizedException("Authorization header missing")

    # Extract token from "Bearer <token>"
    parts = authorization.split()
    if len(parts) != 2 or parts[0].lower() != "bearer":
        raise UnauthorizedException("Invalid authorization header format")

    token = parts[1]

    # Decode and validate token
    payload = decode_token(token)
    if not payload:
        raise UnauthorizedException("Invalid or expired token")

    if payload.get("type") != "access":
        raise UnauthorizedException("Invalid token type")

    user_id = payload.get("sub")
    if not user_id:
        raise UnauthorizedException("Invalid token payload")

    # Get user from database
    user_repo = UserRepository(db)
    user = await user_repo.find_by_id(user_id)

    if not user:
        raise UnauthorizedException("User not found")

    if not user.get("is_active", False):
        raise UnauthorizedException("User account is deactivated")

    # Serialize and return
    user = UserRepository.serialize_doc(user)
    return UserResponse(**user)


# Type alias for cleaner dependency injection
CurrentUser = Annotated[UserResponse, Depends(get_current_user)]
