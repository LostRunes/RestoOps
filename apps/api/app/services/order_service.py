from datetime import datetime, timezone
from decimal import Decimal
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.core.events import Event, EventBus, EventType
from app.models.order import Order
from app.models.order_item import OrderItem
from app.models.quote import Quote
from app.models.lead import Lead
from app.models.lead_activity import LeadActivity
from app.models.audit_log import AuditLog
from app.repositories.order_repo import OrderRepository
from app.services.number_generator import NumberGenerator


VALID_ORDER_TRANSITIONS = {
    "CONFIRMED": ["PREPARING", "CANCELLED"],
    "PREPARING": ["IN_TRANSIT", "CANCELLED"],
    "IN_TRANSIT": ["DELIVERED", "CANCELLED"],
    "DELIVERED": ["COMPLETED", "CANCELLED"],
    "COMPLETED": [],
    "CANCELLED": [],
}


class OrderService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.repo = OrderRepository(db)

    async def create_from_quote(
        self, quote: Quote, org_id: str, user_id: str | None = None
    ) -> Order:
        now = datetime.now(timezone.utc)
        order_number = await NumberGenerator.next_order_number(org_id, self.db)

        order = Order(
            organization_id=org_id,
            restaurant_id=quote.restaurant_id,
            lead_id=quote.lead_id,
            quote_id=quote.id,
            order_number=order_number,
            event_date=quote.event_date,
            guest_count=quote.guest_count,
            total=quote.total,
            status="CONFIRMED",
            special_instructions=quote.notes,
            confirmed_at=now,
        )
        self.db.add(order)
        await self.db.flush()

        for item in quote.items:
            order_item = OrderItem(
                order_id=order.id,
                name=item.name,
                description=item.description,
                quantity=item.quantity,
                unit_price=item.unit_price,
                total=item.total,
            )
            self.db.add(order_item)

        # Update Quote
        quote.status = "ACCEPTED"
        quote.accepted_at = now

        # Update Lead pipeline status
        stmt_lead = select(Lead).where(Lead.id == quote.lead_id).where(Lead.organization_id == org_id)
        res_lead = await self.db.execute(stmt_lead)
        lead = res_lead.scalar_one_or_none()
        if lead:
            lead.pipeline_status = "WON"

        # Lead Activity
        activity = LeadActivity(
            lead_id=quote.lead_id,
            user_id=user_id,
            activity_type="ORDER_CREATED",
            description=f"Order {order_number} created from Quote {quote.quote_number} for total ${quote.total:.2f}",
            activity_metadata={"order_id": order.id, "quote_id": quote.id, "total": str(quote.total)},
        )
        self.db.add(activity)

        # Audit Log
        audit = AuditLog(
            organization_id=org_id,
            user_id=user_id,
            action="ORDER_CREATED",
            entity_type="order",
            entity_id=order.id,
            new_value={"order_number": order_number, "quote_id": quote.id, "total": str(quote.total)},
        )
        self.db.add(audit)

        await self.db.flush()
        order = await self.repo.get_by_id(order.id, org_id)

        await EventBus.publish(Event(
            EventType.ORDER_CREATED, org_id,
            {"order_id": order.id, "order_number": order_number,
             "total": float(quote.total or 0),
             "company_name": lead.company_name if lead else "",
             "quote_id": quote.id, "quote_number": quote.quote_number},
            user_id=user_id,
        ))
        await EventBus.publish(Event(
            EventType.QUOTE_ACCEPTED, org_id,
            {"quote_id": quote.id, "quote_number": quote.quote_number,
             "order_id": order.id, "total": float(quote.total or 0),
             "company_name": lead.company_name if lead else ""},
            user_id=user_id,
        ))
        return order

    async def update_status(
        self, order_id: str, org_id: str, new_status: str, user_id: str | None = None
    ) -> Order:
        order = await self.repo.get_by_id(order_id, org_id)
        if not order:
            raise ValueError(f"Order '{order_id}' not found")

        current_status = order.status
        allowed = VALID_ORDER_TRANSITIONS.get(current_status, [])
        if new_status not in allowed and new_status != current_status:
            raise ValueError(
                f"Invalid status transition from {current_status} to {new_status}. Allowed: {allowed}"
            )

        now = datetime.now(timezone.utc)
        order.status = new_status
        if new_status == "COMPLETED":
            order.completed_at = now
        elif new_status == "CANCELLED":
            order.cancelled_at = now

        audit = AuditLog(
            organization_id=org_id,
            user_id=user_id,
            action="ORDER_STATUS_UPDATED",
            entity_type="order",
            entity_id=order.id,
            old_value={"status": current_status},
            new_value={"status": new_status},
        )
        self.db.add(audit)

        await self.db.flush()
        return order

    async def get_order(self, order_id: str, org_id: str) -> Order:
        order = await self.repo.get_by_id(order_id, org_id)
        if not order:
            raise ValueError(f"Order '{order_id}' not found")
        return order

    async def list_orders(
        self, org_id: str, lead_id: str | None = None, status: str | None = None
    ) -> list[Order]:
        return await self.repo.list_by_org(org_id, lead_id, status)

    async def get_revenue(
        self, org_id: str, start_date=None, end_date=None
    ) -> dict:
        return await self.repo.get_revenue_stats(org_id, start_date, end_date)
