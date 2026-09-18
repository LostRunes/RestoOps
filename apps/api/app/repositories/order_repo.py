from datetime import date, datetime
from decimal import Decimal
from sqlalchemy import extract, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from app.models.order import Order
from app.models.order_item import OrderItem


class OrderRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(self, order: Order) -> Order:
        self.db.add(order)
        await self.db.flush()
        return order

    async def get_by_id(self, order_id: str, org_id: str) -> Order | None:
        stmt = (
            select(Order)
            .where(Order.id == order_id)
            .where(Order.organization_id == org_id)
            .options(selectinload(Order.items))
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_quote_id(self, quote_id: str, org_id: str) -> Order | None:
        stmt = (
            select(Order)
            .where(Order.quote_id == quote_id)
            .where(Order.organization_id == org_id)
            .options(selectinload(Order.items))
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def list_by_org(
        self, org_id: str, lead_id: str | None = None, status: str | None = None
    ) -> list[Order]:
        stmt = (
            select(Order)
            .where(Order.organization_id == org_id)
            .options(selectinload(Order.items))
            .order_by(Order.created_at.desc())
        )
        if lead_id:
            stmt = stmt.where(Order.lead_id == lead_id)
        if status:
            stmt = stmt.where(Order.status == status)

        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def get_revenue_stats(
        self, org_id: str, start_date: date | None = None, end_date: date | None = None
    ) -> dict:
        # Base query excluding CANCELLED orders
        base_where = [Order.organization_id == org_id, Order.status != "CANCELLED"]
        if start_date:
            base_where.append(Order.event_date >= start_date)
        if end_date:
            base_where.append(Order.event_date <= end_date)

        # 1. Total revenue and order count
        stmt_totals = select(
            func.coalesce(func.sum(Order.total), Decimal("0.00")),
            func.count(Order.id),
        ).where(*base_where)
        res_totals = await self.db.execute(stmt_totals)
        total_revenue, order_count = res_totals.one()
        avg_value = (
            (total_revenue / Decimal(order_count)) if order_count > 0 else Decimal("0.00")
        )

        # 2. Breakdown by status
        stmt_status = (
            select(Order.status, func.coalesce(func.sum(Order.total), Decimal("0.00")))
            .where(Order.organization_id == org_id)
            .group_by(Order.status)
        )
        res_status = await self.db.execute(stmt_status)
        by_status = {status: revenue for status, revenue in res_status.all()}

        # 3. Monthly revenue breakdown
        stmt_monthly = (
            select(
                extract("year", Order.event_date).label("yr"),
                extract("month", Order.event_date).label("mo"),
                func.coalesce(func.sum(Order.total), Decimal("0.00")),
            )
            .where(*base_where)
            .group_by("yr", "mo")
            .order_by("yr", "mo")
        )
        res_monthly = await self.db.execute(stmt_monthly)
        by_month = [
            {"month": f"{int(yr):04d}-{int(mo):02d}", "revenue": revenue}
            for yr, mo, revenue in res_monthly.all()
        ]

        return {
            "total_revenue": total_revenue,
            "order_count": order_count,
            "average_order_value": round(avg_value, 2),
            "by_status": by_status,
            "by_month": by_month,
        }
