"""User management endpoints."""

from fastapi import APIRouter, Depends
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.api.deps import CurrentUser
from app.db.mongodb import get_db
from app.schemas.auth import MessageResponse
from app.schemas.user import UserResponse, UserUpdate
from app.services.user_service import UserService

router = APIRouter(prefix="/users", tags=["users"])


@router.get(
    "/me",
    response_model=UserResponse,
    summary="Get current user",
)
async def get_current_user_info(
    current_user: CurrentUser,
) -> UserResponse:
    """
    Get the currently authenticated user's information.
    """
    return current_user


@router.put(
    "/me",
    response_model=UserResponse,
    summary="Update current user",
)
async def update_current_user(
    data: UserUpdate,
    current_user: CurrentUser,
    db: AsyncIOMotorDatabase = Depends(get_db),
) -> UserResponse:
    """
    Update the current user's information.
    """
    service = UserService(db)
    return await service.update(current_user.id, data)


@router.delete(
    "/me",
    response_model=MessageResponse,
    summary="Delete current user",
)
async def delete_current_user(
    current_user: CurrentUser,
    db: AsyncIOMotorDatabase = Depends(get_db),
) -> MessageResponse:
    """
    Delete (deactivate) the current user's account.
    """
    service = UserService(db)
    await service.delete(current_user.id)
    return MessageResponse(message="Account deleted successfully")
