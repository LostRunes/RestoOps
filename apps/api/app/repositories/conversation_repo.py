from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from app.models.conversation import Conversation


class ConversationRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(
        self,
        org_id: str,
        lead_id: str,
        channel: str = "EMAIL",
        restaurant_id: str | None = None,
        subject: str | None = None,
    ) -> Conversation:
        conv = Conversation(
            organization_id=org_id,
            restaurant_id=restaurant_id,
            lead_id=lead_id,
            channel=channel,
            subject=subject,
            status="OPEN",
            message_count=0,
        )
        self.db.add(conv)
        await self.db.commit()
        await self.db.refresh(conv)
        return conv

    async def get_by_id(self, conv_id: str, org_id: str) -> Conversation | None:
        stmt = (
            select(Conversation)
            .options(
                selectinload(Conversation.lead),
                selectinload(Conversation.messages),
            )
            .where(Conversation.id == conv_id, Conversation.organization_id == org_id)
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def list_by_org(self, org_id: str, filters: dict | None = None) -> list[Conversation]:
        stmt = (
            select(Conversation)
            .options(selectinload(Conversation.lead))
            .where(Conversation.organization_id == org_id)
        )

        if filters:
            if "status" in filters and filters["status"]:
                stmt = stmt.where(Conversation.status == filters["status"])
            if "lead_id" in filters and filters["lead_id"]:
                stmt = stmt.where(Conversation.lead_id == filters["lead_id"])

        stmt = stmt.order_by(Conversation.updated_at.desc())
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def get_by_lead(self, lead_id: str, org_id: str, channel: str = "EMAIL") -> Conversation | None:
        stmt = (
            select(Conversation)
            .where(
                Conversation.lead_id == lead_id,
                Conversation.organization_id == org_id,
                Conversation.channel == channel,
            )
            .order_by(Conversation.updated_at.desc())
        )
        result = await self.db.execute(stmt)
        return result.scalars().first()

    async def update(self, conv_id: str, **data) -> None:
        stmt = update(Conversation).where(Conversation.id == conv_id).values(**data)
        await self.db.execute(stmt)
        await self.db.commit()
