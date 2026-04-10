"""Audit log repository."""

from __future__ import annotations

from typing import Any, Optional

from motor.motor_asyncio import AsyncIOMotorDatabase

from app.db.repositories.base import BaseRepository


class AuditRepository(BaseRepository):
    """Repository for audit log persistence."""

    def __init__(self, db: AsyncIOMotorDatabase):
        super().__init__(db, "audit_logs")

    async def create_log(
        self,
        *,
        user_id: str,
        action: str,
        resource_type: str,
        resource_id: Optional[str],
        details: Optional[dict[str, Any]] = None,
    ) -> str:
        """Create a new audit log entry."""
        return await self.insert_one(
            {
                "user_id": user_id,
                "action": action,
                "resource_type": resource_type,
                "resource_id": resource_id,
                "details": details or {},
            }
        )
