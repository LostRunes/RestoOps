from datetime import datetime, timezone
from decimal import Decimal
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.core.events import Event, EventBus, EventType
from app.models.quote import Quote
from app.models.quote_item import QuoteItem
from app.models.lead import Lead
from app.models.restaurant import Restaurant
from app.models.lead_activity import LeadActivity
from app.models.audit_log import AuditLog
from app.models.message import Message
from app.repositories.quote_repo import QuoteRepository
from app.services.number_generator import NumberGenerator
from app.services.quote_email_renderer import QuoteEmailRenderer
from app.services.email_service import EmailService
from app.services.order_service import OrderService


class QuoteService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.repo = QuoteRepository(db)
        self.email_renderer = QuoteEmailRenderer()
        self.email_service = EmailService()

    async def _recalculate_quote_totals(self, quote: Quote) -> Quote:
        subtotal = Decimal("0.00")
        for item in quote.items:
            item.total = Decimal(str(item.quantity)) * Decimal(str(item.unit_price))
            subtotal += item.total

        quote.subtotal = subtotal
        tax_rate = Decimal(str(quote.tax_rate or 0))
        quote.tax = round(subtotal * tax_rate, 2)
        delivery = Decimal(str(quote.delivery_fee or 0))
        discount = Decimal(str(quote.discount or 0))
        quote.total = subtotal + quote.tax + delivery - discount
        await self.db.flush()
        return quote

    async def create_quote(
        self,
        org_id: str,
        restaurant_id: str,
        lead_id: str,
        event_date,
        guest_count: int,
        items: list[dict],
        event_type: str | None = None,
        tax_rate: Decimal | float | int = 0.0,
        delivery_fee: Decimal | float | int = 0.0,
        discount: Decimal | float | int = 0.0,
        notes: str | None = None,
        terms: str | None = None,
        conversation_id: str | None = None,
        ai_run_id: str | None = None,
        valid_until=None,
        created_by: str | None = None,
    ) -> Quote:
        quote_number = await NumberGenerator.next_quote_number(org_id, self.db)

        tax_rate_dec = Decimal(str(tax_rate))
        delivery_dec = Decimal(str(delivery_fee))
        discount_dec = Decimal(str(discount))

        quote = Quote(
            organization_id=org_id,
            restaurant_id=restaurant_id,
            lead_id=lead_id,
            conversation_id=conversation_id,
            ai_run_id=ai_run_id,
            event_date=event_date,
            event_type=event_type,
            guest_count=guest_count,
            tax_rate=tax_rate_dec,
            delivery_fee=delivery_dec,
            discount=discount_dec,
            notes=notes,
            terms=terms,
            status="DRAFT",
            quote_number=quote_number,
            valid_until=valid_until,
            created_by=created_by,
        )
        self.db.add(quote)
        await self.db.flush()

        for idx, item_data in enumerate(items):
            qty = int(item_data.get("quantity", 1))
            price = Decimal(str(item_data.get("unit_price", 0)))
            item_total = Decimal(str(qty)) * price
            quote_item = QuoteItem(
                quote_id=quote.id,
                name=item_data["name"],
                description=item_data.get("description"),
                category=item_data.get("category", "FOOD"),
                quantity=qty,
                unit_price=price,
                total=item_total,
                sort_order=idx,
            )
            self.db.add(quote_item)

        await self.db.flush()
        # Reload quote with items to calculate totals
        quote = await self.repo.get_by_id(quote.id, org_id)
        await self._recalculate_quote_totals(quote)

        # Log Lead Activity
        activity = LeadActivity(
            lead_id=lead_id,
            user_id=created_by,
            activity_type="QUOTE_CREATED",
            description=f"Draft quote {quote_number} created for ${quote.total:.2f}",
            activity_metadata={"quote_id": quote.id, "total": str(quote.total)},
        )
        self.db.add(activity)
        await self.db.flush()

        return quote

    async def get_quote(self, quote_id: str, org_id: str) -> Quote:
        quote = await self.repo.get_by_id(quote_id, org_id)
        if not quote:
            raise ValueError(f"Quote '{quote_id}' not found")
        return quote

    async def list_quotes(
        self, org_id: str, lead_id: str | None = None, status: str | None = None
    ) -> list[Quote]:
        return await self.repo.list_by_org(org_id, lead_id, status)

    async def update_quote(self, quote_id: str, org_id: str, **data) -> Quote:
        quote = await self.get_quote(quote_id, org_id)
        if quote.status not in ["DRAFT", "PENDING_APPROVAL"]:
            raise ValueError(f"Cannot update quote in status '{quote.status}'")

        for key, value in data.items():
            if hasattr(quote, key) and value is not None:
                if key in ["tax_rate", "delivery_fee", "discount"]:
                    setattr(quote, key, Decimal(str(value)))
                else:
                    setattr(quote, key, value)

        await self._recalculate_quote_totals(quote)
        return quote

    async def add_item(self, quote_id: str, org_id: str, **item_data) -> QuoteItem:
        quote = await self.get_quote(quote_id, org_id)
        if quote.status not in ["DRAFT", "PENDING_APPROVAL"]:
            raise ValueError(f"Cannot add items to quote in status '{quote.status}'")

        qty = int(item_data.get("quantity", 1))
        price = Decimal(str(item_data.get("unit_price", 0)))
        item_total = Decimal(str(qty)) * price

        item = QuoteItem(
            quote_id=quote.id,
            name=item_data["name"],
            description=item_data.get("description"),
            category=item_data.get("category", "FOOD"),
            quantity=qty,
            unit_price=price,
            total=item_total,
            sort_order=len(quote.items),
        )
        self.db.add(item)
        await self.db.flush()

        # Refresh quote items and recalculate
        self.db.expire(quote, ["items"])
        quote = await self.repo.get_by_id(quote_id, org_id)
        await self._recalculate_quote_totals(quote)
        return item

    async def remove_item(self, quote_id: str, org_id: str, item_id: str) -> None:
        quote = await self.get_quote(quote_id, org_id)
        if quote.status not in ["DRAFT", "PENDING_APPROVAL"]:
            raise ValueError(f"Cannot remove items from quote in status '{quote.status}'")

        item = await self.repo.get_item(item_id, quote_id)
        if not item:
            raise ValueError(f"Item '{item_id}' not found on quote '{quote_id}'")

        await self.repo.remove_item(item)
        self.db.expire(quote, ["items"])
        quote = await self.repo.get_by_id(quote_id, org_id)
        await self._recalculate_quote_totals(quote)

    async def submit_for_approval(self, quote_id: str, org_id: str) -> Quote:
        quote = await self.get_quote(quote_id, org_id)
        if quote.status != "DRAFT":
            raise ValueError(f"Only DRAFT quotes can be submitted for approval (current: {quote.status})")

        quote.status = "PENDING_APPROVAL"
        await self.db.flush()
        return quote

    async def approve_quote(self, quote_id: str, org_id: str, user_id: str | None = None) -> Quote:
        quote = await self.get_quote(quote_id, org_id)
        if quote.status != "PENDING_APPROVAL":
            raise ValueError(f"Only PENDING_APPROVAL quotes can be approved (current: {quote.status})")

        quote.status = "DRAFT"  # Approved draft, ready to send
        audit = AuditLog(
            organization_id=org_id,
            user_id=user_id,
            action="QUOTE_APPROVED",
            entity_type="quote",
            entity_id=quote.id,
            new_value={"status": "DRAFT", "approved_by": user_id},
        )
        self.db.add(audit)
        await self.db.flush()
        return quote

    async def send_quote(self, quote_id: str, org_id: str, user_id: str | None = None) -> Quote:
        quote = await self.get_quote(quote_id, org_id)
        if quote.status not in ["DRAFT", "PENDING_APPROVAL"]:
            raise ValueError(f"Quote status '{quote.status}' cannot be sent")

        # Fetch Lead and Restaurant
        res_lead = await self.db.execute(
            select(Lead).where(Lead.id == quote.lead_id).where(Lead.organization_id == org_id)
        )
        lead = res_lead.scalar_one_or_none()
        if not lead or not lead.email:
            raise ValueError("Lead does not exist or has no email address")

        res_rest = await self.db.execute(
            select(Restaurant).where(Restaurant.id == quote.restaurant_id)
        )
        restaurant = res_rest.scalar_one_or_none()

        # Render Email
        html_body, text_body = self.email_renderer.render(quote, quote.items, lead, restaurant)
        subject = f"Catering Proposal #{quote.quote_number} for {quote.event_type or 'Your Event'}"

        # Send Email via EmailService
        await self.email_service.send_email(
            to=lead.email,
            subject=subject,
            body_html=html_body,
            body_text=text_body,
            from_addr=None,
        )

        now = datetime.now(timezone.utc)
        quote.status = "SENT"
        quote.sent_at = now

        # Update Lead status
        lead.pipeline_status = "QUOTE_SENT"

        # Record Message in conversation if conversation exists
        if quote.conversation_id:
            msg = Message(
                conversation_id=quote.conversation_id,
                sender_type="USER",
                sender_id=user_id,
                channel="EMAIL",
                subject=subject,
                body=text_body,
                created_at=now,
            )
            self.db.add(msg)

        # Activity & Audit
        activity = LeadActivity(
            lead_id=lead.id,
            user_id=user_id,
            activity_type="QUOTE_SENT",
            description=f"Quote #{quote.quote_number} sent to {lead.email}",
            activity_metadata={"quote_id": quote.id, "total": str(quote.total)},
        )
        self.db.add(activity)

        audit = AuditLog(
            organization_id=org_id,
            user_id=user_id,
            action="QUOTE_SENT",
            entity_type="quote",
            entity_id=quote.id,
            new_value={"quote_number": quote.quote_number, "sent_to": lead.email},
        )
        self.db.add(audit)

        await self.db.flush()

        await EventBus.publish(Event(
            EventType.QUOTE_SENT, org_id,
            {"quote_id": quote.id, "quote_number": quote.quote_number,
             "lead_email": lead.email, "total": float(quote.total or 0),
             "company_name": lead.company_name},
            user_id=user_id,
        ))
        return quote

    async def accept_quote(self, quote_id: str, org_id: str, user_id: str | None = None):
        quote = await self.get_quote(quote_id, org_id)
        if quote.status in ["ACCEPTED", "EXPIRED"]:
            raise ValueError(f"Quote status is already '{quote.status}'")

        order_service = OrderService(self.db)
        return await order_service.create_from_quote(quote, org_id, user_id)


    async def reject_quote(self, quote_id: str, org_id: str, user_id: str | None = None) -> Quote:
        quote = await self.get_quote(quote_id, org_id)
        now = datetime.now(timezone.utc)
        quote.status = "REJECTED"
        quote.rejected_at = now

        activity = LeadActivity(
            lead_id=quote.lead_id,
            user_id=user_id,
            activity_type="QUOTE_REJECTED",
            description=f"Quote #{quote.quote_number} was rejected",
            activity_metadata={"quote_id": quote.id},
        )
        self.db.add(activity)

        audit = AuditLog(
            organization_id=org_id,
            user_id=user_id,
            action="QUOTE_REJECTED",
            entity_type="quote",
            entity_id=quote.id,
            new_value={"quote_number": quote.quote_number},
        )
        self.db.add(audit)

        await self.db.flush()

        await EventBus.publish(Event(
            EventType.QUOTE_REJECTED, org_id,
            {"quote_id": quote.id, "quote_number": quote.quote_number,
             "company_name": ""},
            user_id=user_id,
        ))
        return quote

    async def mark_viewed(self, quote_id: str, org_id: str) -> Quote:
        quote = await self.get_quote(quote_id, org_id)
        if quote.status == "SENT":
            quote.status = "VIEWED"
            quote.viewed_at = datetime.now(timezone.utc)
            await self.db.flush()
        return quote

    async def check_expirations(self) -> list[Quote]:
        expired_quotes = await self.repo.get_expired_quotes()
        now = datetime.now(timezone.utc)
        for q in expired_quotes:
            q.status = "EXPIRED"
            activity = LeadActivity(
                lead_id=q.lead_id,
                activity_type="QUOTE_EXPIRED",
                description=f"Quote #{q.quote_number} has expired",
                activity_metadata={"quote_id": q.id},
            )
            self.db.add(activity)
        await self.db.flush()
        for q in expired_quotes:
            await EventBus.publish(Event(
                EventType.QUOTE_EXPIRED, q.organization_id,
                {"quote_id": q.id, "quote_number": q.quote_number},
            ))
        return expired_quotes
