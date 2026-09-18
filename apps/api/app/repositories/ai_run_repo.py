"""
Repository for AI Runs.
"""
from __future__ import annotations
from uuid import uuid4
from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.ai_run import AIRun


class AIRunRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(
        self,
        org_id: str,
        agent: str,
        model: str,
        input_text: str,
        output_text: str,
        structured_output: dict | None,
        latency_ms: int,
        tokens: int | None,
        status: str,
        error: str | None = None,
        conversation_id: str | None = None,
        lead_id: str | None = None,
    ) -> AIRun:
        run = AIRun(
            id=str(uuid4()),
            organization_id=org_id,
            agent=agent,
            model=model,
            input=input_text,
            output=output_text,
            structured_output=structured_output,
            latency_ms=latency_ms,
            tokens_used=tokens,
            status=status,
            error=error,
            conversation_id=conversation_id,
            lead_id=lead_id,
        )
        self.db.add(run)
        await self.db.flush()
        return run

    async def get_by_id(self, run_id: str, org_id: str) -> AIRun | None:
        result = await self.db.execute(
            select(AIRun).where(
                AIRun.id == run_id,
                AIRun.organization_id == org_id,
            )
        )
        return result.scalar_one_or_none()

    async def list_by_org(
        self, org_id: str, page: int = 1, page_size: int = 20
    ) -> list[AIRun]:
        offset = (page - 1) * page_size
        result = await self.db.execute(
            select(AIRun)
            .where(AIRun.organization_id == org_id)
            .order_by(desc(AIRun.created_at))
            .offset(offset)
            .limit(page_size)
        )
        return list(result.scalars().all())
