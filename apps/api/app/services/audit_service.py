"""
Audit logging service — records important state changes for compliance and debugging.
"""
from __future__ import annotations
from uuid import uuid4
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.audit_log import AuditLog
from app.core.logging import logger


class AuditService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def log(
        self,
        org_id: str,
        action: str,
        entity_type: str,
        entity_id: str,
        user_id: str | None = None,
        old_value: dict | None = None,
        new_value: dict | None = None,
        ip_address: str | None = None,
        user_agent: str | None = None,
    ) -> AuditLog:
        """Create an audit log entry."""
        entry = AuditLog(
            id=str(uuid4()),
            organization_id=org_id,
            user_id=user_id,
            action=action,
            entity_type=entity_type,
            entity_id=entity_id,
            old_value=old_value,
            new_value=new_value,
            ip_address=ip_address,
            user_agent=user_agent,
        )
        self.db.add(entry)
        await self.db.flush()
        logger.info(
            "audit_log_created",
            org_id=org_id,
            action=action,
            entity_type=entity_type,
            entity_id=entity_id,
            user_id=user_id,
        )
        return entry
