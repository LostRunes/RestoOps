"""
Repository for AI Actions (human-in-the-loop approvals).
"""
from __future__ import annotations
from uuid import uuid4
from datetime import datetime, timezone
from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.ai_action import AIAction


class AIActionRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(
        self,
        ai_run_id: str,
        org_id: str,
        tool: str,
        arguments: dict,
        status: str = "PROPOSED",
    ) -> AIAction:
        action = AIAction(
            id=str(uuid4()),
            ai_run_id=ai_run_id,
            organization_id=org_id,
            tool=tool,
            arguments=arguments,
            status=status,
        )
        self.db.add(action)
        await self.db.flush()
        return action

    async def get_by_id(self, action_id: str, org_id: str) -> AIAction | None:
        result = await self.db.execute(
            select(AIAction).where(
                AIAction.id == action_id,
                AIAction.organization_id == org_id,
            )
        )
        return result.scalar_one_or_none()

    async def update(self, action_id: str, **data) -> AIAction | None:
        result = await self.db.execute(
            select(AIAction).where(AIAction.id == action_id)
        )
        action = result.scalar_one_or_none()
        if action:
            for key, val in data.items():
                setattr(action, key, val)
            await self.db.flush()
        return action

    async def list_pending(self, org_id: str) -> list[AIAction]:
        result = await self.db.execute(
            select(AIAction)
            .where(
                AIAction.organization_id == org_id,
                AIAction.status == "PROPOSED",
            )
            .order_by(desc(AIAction.created_at))
        )
        return list(result.scalars().all())

    async def list_by_run(self, ai_run_id: str) -> list[AIAction]:
        result = await self.db.execute(
            select(AIAction)
            .where(AIAction.ai_run_id == ai_run_id)
            .order_by(AIAction.created_at)
        )
        return list(result.scalars().all())
