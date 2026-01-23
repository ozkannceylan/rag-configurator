"""User model."""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field, EmailStr


class User(BaseModel):
    """User account model."""
    id: Optional[str] = Field(default=None, alias="_id")
    email: EmailStr
    name: str = Field(..., min_length=1, max_length=100)
    password_hash: Optional[str] = Field(default=None, exclude=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    is_active: bool = Field(default=True)

    model_config = {
        "populate_by_name": True,
        "json_encoders": {
            datetime: lambda v: v.isoformat()
        }
    }
