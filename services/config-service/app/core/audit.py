"""Audit logging helpers."""

from __future__ import annotations

from typing import Any, Optional

from motor.motor_asyncio import AsyncIOMotorDatabase

from app.db.repositories.audit_repo import AuditRepository


class AuditLogger:
    """Best-effort audit logger for state-changing config-service operations."""

    def __init__(self, db: AsyncIOMotorDatabase):
        self.repo = AuditRepository(db)

    async def log(
        self,
        *,
        user_id: str,
        action: str,
        resource_type: str,
        resource_id: Optional[str],
        details: Optional[dict[str, Any]] = None,
    ) -> str:
        """Persist an audit log entry."""
        return await self.repo.create_log(
            user_id=user_id,
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            details=details,
        )
