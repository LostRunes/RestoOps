from datetime import datetime, timezone
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.call import Call
from app.models.call_event import CallEvent


class CallRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(self, **data) -> Call:
        call = Call(**data)
        self.db.add(call)
        await self.db.flush()
        await self.db.refresh(call)
        return call

    async def get_by_id(self, call_id: str, org_id: str) -> Call | None:
        stmt = (
            select(Call)
            .options(selectinload(Call.events))
            .where(Call.id == call_id, Call.organization_id == org_id)
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_exotel_sid(self, call_sid: str) -> Call | None:
        stmt = select(Call).where(Call.exotel_call_sid == call_sid)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_webrtc_room(self, room_id: str) -> Call | None:
        """WebRTC calls store the room_id in exotel_call_sid field for uniformity."""
        return await self.get_by_exotel_sid(room_id)

    async def list_by_org(
        self,
        org_id: str,
        lead_id: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[Call]:
        stmt = (
            select(Call)
            .where(Call.organization_id == org_id)
            .order_by(Call.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        if lead_id:
            stmt = stmt.where(Call.lead_id == lead_id)
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def update(self, call_id: str, **data) -> Call | None:
        stmt = select(Call).where(Call.id == call_id)
        result = await self.db.execute(stmt)
        call = result.scalar_one_or_none()
        if not call:
            return None
        for key, val in data.items():
            setattr(call, key, val)
        await self.db.flush()
        await self.db.refresh(call)
        return call

    async def add_event(
        self,
        call_id: str,
        event_type: str,
        payload: dict | None = None,
        source: str = "SYSTEM",
    ) -> CallEvent:
        event = CallEvent(
            call_id=call_id,
            event_type=event_type,
            payload=payload,
            source=source,
        )
        self.db.add(event)
        await self.db.flush()
        return event

    async def get_events(self, call_id: str) -> list[CallEvent]:
        stmt = (
            select(CallEvent)
            .where(CallEvent.call_id == call_id)
            .order_by(CallEvent.created_at)
        )
        result = await self.db.execute(stmt)
        return list(result.scalars().all())
