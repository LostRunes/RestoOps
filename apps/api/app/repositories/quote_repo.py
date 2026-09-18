from datetime import datetime, timezone
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from app.models.quote import Quote
from app.models.quote_item import QuoteItem


class QuoteRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(self, quote: Quote) -> Quote:
        self.db.add(quote)
        await self.db.flush()
        return quote

    async def get_by_id(self, quote_id: str, org_id: str) -> Quote | None:
        stmt = (
            select(Quote)
            .where(Quote.id == quote_id)
            .where(Quote.organization_id == org_id)
            .options(selectinload(Quote.items))
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def list_by_org(
        self, org_id: str, lead_id: str | None = None, status: str | None = None
    ) -> list[Quote]:
        stmt = (
            select(Quote)
            .where(Quote.organization_id == org_id)
            .options(selectinload(Quote.items))
            .order_by(Quote.created_at.desc())
        )
        if lead_id:
            stmt = stmt.where(Quote.lead_id == lead_id)
        if status:
            stmt = stmt.where(Quote.status == status)

        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def add_item(self, item: QuoteItem) -> QuoteItem:
        self.db.add(item)
        await self.db.flush()
        return item

    async def get_item(self, item_id: str, quote_id: str) -> QuoteItem | None:
        stmt = select(QuoteItem).where(QuoteItem.id == item_id).where(QuoteItem.quote_id == quote_id)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def remove_item(self, item: QuoteItem) -> None:
        await self.db.delete(item)
        await self.db.flush()

    async def get_expired_quotes(self) -> list[Quote]:
        now = datetime.now(timezone.utc)
        stmt = (
            select(Quote)
            .where(Quote.status == "SENT")
            .where(Quote.expires_at.isnot(None))
            .where(Quote.expires_at < now)
        )
        result = await self.db.execute(stmt)
        return list(result.scalars().all())
