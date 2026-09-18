from datetime import datetime, timezone
from sqlalchemy import extract, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.quote import Quote
from app.models.order import Order


class NumberGenerator:
    @staticmethod
    async def next_quote_number(org_id: str, db: AsyncSession) -> str:
        current_year = datetime.now(timezone.utc).year
        stmt = (
            select(func.count(Quote.id))
            .where(Quote.organization_id == org_id)
            .where(extract("year", Quote.created_at) == current_year)
        )
        result = await db.execute(stmt)
        count = result.scalar() or 0
        seq = count + 1
        return f"Q-{current_year}-{seq:04d}"

    @staticmethod
    async def next_order_number(org_id: str, db: AsyncSession) -> str:
        current_year = datetime.now(timezone.utc).year
        stmt = (
            select(func.count(Order.id))
            .where(Order.organization_id == org_id)
            .where(extract("year", Order.created_at) == current_year)
        )
        result = await db.execute(stmt)
        count = result.scalar() or 0
        seq = count + 1
        return f"ORD-{current_year}-{seq:04d}"
