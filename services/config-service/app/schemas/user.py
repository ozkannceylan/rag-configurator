"""User schemas for request/response."""

from datetime import datetime
from typing import Optional
from pydantic import BaseModel, EmailStr, Field


class UserResponse(BaseModel):
    """User response schema."""

    id: str
    email: EmailStr
    name: str
    created_at: datetime
    updated_at: datetime
    is_active: bool

    model_config = {"from_attributes": True}


class UserUpdate(BaseModel):
    """User update request schema."""

    name: Optional[str] = Field(None, min_length=1, max_length=100)
    email: Optional[EmailStr] = None
