import asyncio
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
import pytest
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker

from app.db.base import Base
from app.models.organization import Organization
from app.models.restaurant import Restaurant
from app.models.lead import Lead
from app.models.quote import Quote
from app.models.quote_item import QuoteItem
from app.models.order import Order
from app.models.order_item import OrderItem
from app.services.number_generator import NumberGenerator
from app.services.quote_email_renderer import QuoteEmailRenderer
from app.services.quote_service import QuoteService
from app.services.order_service import OrderService

DATABASE_URL = "postgresql+asyncpg://restoops_user:restoops_password_dev_123@localhost:5432/restoops_db"


@pytest.fixture
def anyio_backend():
    return "asyncio"


def test_number_generator():
    """Test sequential quote and order number generation logic."""
    async def _test():
        engine = create_async_engine(DATABASE_URL)
        async_session = async_sessionmaker(engine, expire_on_commit=False)
        async with async_session() as db:
            org = Organization(name="Test Org Numbers", slug="test-org-numbers")
            db.add(org)
            await db.flush()

            q_num1 = await NumberGenerator.next_quote_number(org.id, db)
            o_num1 = await NumberGenerator.next_order_number(org.id, db)

            assert q_num1.startswith("Q-")
            assert o_num1.startswith("ORD-")
            assert q_num1.endswith("-0001")
            assert o_num1.endswith("-0001")

            await db.rollback()
        await engine.dispose()

    asyncio.run(_test())


def test_quote_email_renderer():
    """Test HTML and text rendering of catering quotes."""
    quote = Quote(
        quote_number="Q-2026-0099",
        event_date=date(2026, 10, 15),
        event_type="Corporate Gala",
        guest_count=150,
        subtotal=Decimal("1500.00"),
        tax_rate=Decimal("0.1000"),
        tax=Decimal("150.00"),
        delivery_fee=Decimal("50.00"),
        discount=Decimal("100.00"),
        total=Decimal("1600.00"),
        notes="All food served hot in chaffing dishes.",
        valid_until=date(2026, 10, 1),
    )
    items = [
        QuoteItem(name="Buffet Package", description="Plated lunch", quantity=150, unit_price=Decimal("10.00"), total=Decimal("1500.00"))
    ]
    lead = Lead(contact_name="Jane Doe", email="jane@acme.com", company_name="Acme Corp")
    restaurant = Restaurant(name="Gourmet Bistro", phone="555-0199")

    renderer = QuoteEmailRenderer()
    html, text = renderer.render(quote, items, lead, restaurant)

    assert "Q-2026-0099" in html
    assert "Gourmet Bistro" in html
    assert "Jane Doe" in html
    assert "$1600.00" in html
    assert "Buffet Package" in html

    assert "Q-2026-0099" in text
    assert "$1600.00" in text
    assert "Buffet Package" in text


def test_quote_service_lifecycle_and_pricing():
    """Test creating quote, adding/removing items, pricing recalculation, approval, and sending."""
    async def _test():
        engine = create_async_engine(DATABASE_URL)
        async_session = async_sessionmaker(engine, expire_on_commit=False)
        async with async_session() as db:
            org = Organization(name="Quote Lifecycle Org", slug="quote-lifecycle-org")
            db.add(org)
            await db.flush()

            rest = Restaurant(organization_id=org.id, name="Bistro Premier")
            lead = Lead(organization_id=org.id, contact_name="John Smith", email="john@example.com")
            db.add_all([rest, lead])
            await db.flush()

            service = QuoteService(db)
            quote = await service.create_quote(
                org_id=org.id,
                restaurant_id=rest.id,
                lead_id=lead.id,
                event_date=date(2026, 11, 20),
                guest_count=50,
                event_type="Wedding Reception",
                tax_rate=Decimal("0.0800"),
                delivery_fee=Decimal("40.00"),
                discount=Decimal("20.00"),
                items=[
                    {"name": "Appetizer Platter", "quantity": 5, "unit_price": 40.00},
                    {"name": "Main Course", "quantity": 50, "unit_price": 20.00},
                ],
            )

            # Subtotal: (5*40) + (50*20) = 200 + 1000 = 1200
            # Tax: 1200 * 0.08 = 96
            # Total: 1200 + 96 + 40 - 20 = 1316
            assert quote.subtotal == Decimal("1200.00")
            assert quote.tax == Decimal("96.00")
            assert quote.total == Decimal("1316.00")
            assert quote.status == "DRAFT"

            # Add Item
            new_item = await service.add_item(
                quote.id, org.id, name="Dessert", quantity=50, unit_price=5.00
            )
            # New subtotal: 1200 + 250 = 1450
            # New tax: 1450 * 0.08 = 116
            # New total: 1450 + 116 + 40 - 20 = 1586
            quote = await service.get_quote(quote.id, org.id)
            assert quote.subtotal == Decimal("1450.00")
            assert quote.tax == Decimal("116.00")
            assert quote.total == Decimal("1586.00")

            # Remove Item
            await service.remove_item(quote.id, org.id, new_item.id)
            quote = await service.get_quote(quote.id, org.id)
            assert quote.subtotal == Decimal("1200.00")

            # Approval Flow
            quote = await service.submit_for_approval(quote.id, org.id)
            assert quote.status == "PENDING_APPROVAL"

            quote = await service.approve_quote(quote.id, org.id)
            assert quote.status == "DRAFT"

            # Send Quote
            quote = await service.send_quote(quote.id, org.id)
            assert quote.status == "SENT"
            assert quote.sent_at is not None
            assert lead.pipeline_status == "QUOTE_SENT"

            await db.rollback()
        await engine.dispose()

    asyncio.run(_test())


def test_quote_acceptance_creates_order():
    """Test accepting a quote converts it into a confirmed Order with matching items."""
    async def _test():
        engine = create_async_engine(DATABASE_URL)
        async_session = async_sessionmaker(engine, expire_on_commit=False)
        async with async_session() as db:
            org = Organization(name="Order Conversion Org", slug="order-conversion-org")
            db.add(org)
            await db.flush()

            rest = Restaurant(organization_id=org.id, name="Catering Express")
            lead = Lead(organization_id=org.id, contact_name="Alice Wonder", email="alice@wonder.com")
            db.add_all([rest, lead])
            await db.flush()

            q_service = QuoteService(db)
            quote = await q_service.create_quote(
                org_id=org.id,
                restaurant_id=rest.id,
                lead_id=lead.id,
                event_date=date(2026, 12, 1),
                guest_count=80,
                items=[{"name": "Luncheon Package", "quantity": 80, "unit_price": 15.00}],
            )
            quote = await q_service.send_quote(quote.id, org.id)

            # Accept quote
            order = await q_service.accept_quote(quote.id, org.id)

            assert order is not None
            assert order.order_number.startswith("ORD-")
            assert order.quote_id == quote.id
            assert order.status == "CONFIRMED"
            assert order.total == quote.total
            assert len(order.items) == 1
            assert order.items[0].name == "Luncheon Package"
            assert quote.status == "ACCEPTED"
            assert lead.pipeline_status == "WON"

            await db.rollback()
        await engine.dispose()

    asyncio.run(_test())


def test_order_status_transitions_and_revenue():
    """Test order status workflow validation and revenue reporting."""
    async def _test():
        engine = create_async_engine(DATABASE_URL)
        async_session = async_sessionmaker(engine, expire_on_commit=False)
        async with async_session() as db:
            org = Organization(name="Revenue Test Org", slug="revenue-test-org")
            db.add(org)
            await db.flush()

            rest = Restaurant(organization_id=org.id, name="Revenue Resto")
            lead = Lead(organization_id=org.id, contact_name="Bob Builder", email="bob@build.com")
            db.add_all([rest, lead])
            await db.flush()

            q_service = QuoteService(db)
            o_service = OrderService(db)

            # Create 2 quotes & accept them
            q1 = await q_service.create_quote(
                org_id=org.id, restaurant_id=rest.id, lead_id=lead.id,
                event_date=date(2026, 9, 10), guest_count=20,
                items=[{"name": "Meal 1", "quantity": 20, "unit_price": 50.00}],
            )
            await q_service.send_quote(q1.id, org.id)
            ord1 = await q_service.accept_quote(q1.id, org.id)

            q2 = await q_service.create_quote(
                org_id=org.id, restaurant_id=rest.id, lead_id=lead.id,
                event_date=date(2026, 9, 15), guest_count=10,
                items=[{"name": "Meal 2", "quantity": 10, "unit_price": 30.00}],
            )
            await q_service.send_quote(q2.id, org.id)
            ord2 = await q_service.accept_quote(q2.id, org.id)

            # Transition ord1: CONFIRMED -> PREPARING -> IN_TRANSIT -> DELIVERED -> COMPLETED
            await o_service.update_status(ord1.id, org.id, "PREPARING")
            await o_service.update_status(ord1.id, org.id, "IN_TRANSIT")
            await o_service.update_status(ord1.id, org.id, "DELIVERED")
            ord1_updated = await o_service.update_status(ord1.id, org.id, "COMPLETED")
            assert ord1_updated.status == "COMPLETED"
            assert ord1_updated.completed_at is not None

            # Revenue stats
            stats = await o_service.get_revenue(org.id)
            assert stats["total_revenue"] == Decimal("1300.00")
            assert stats["order_count"] == 2
            assert stats["average_order_value"] == Decimal("650.00")
            assert stats["by_status"]["COMPLETED"] == Decimal("1000.00")
            assert stats["by_status"]["CONFIRMED"] == Decimal("300.00")

            await db.rollback()
        await engine.dispose()

    asyncio.run(_test())


def test_quote_expirations():
    """Test quote expiration detection service."""
    async def _test():
        engine = create_async_engine(DATABASE_URL)
        async_session = async_sessionmaker(engine, expire_on_commit=False)
        async with async_session() as db:
            org = Organization(name="Expiration Org", slug="expiration-org")
            db.add(org)
            await db.flush()

            rest = Restaurant(organization_id=org.id, name="Exp Resto")
            lead = Lead(organization_id=org.id, contact_name="Carl Old", email="carl@old.com")
            db.add_all([rest, lead])
            await db.flush()

            q_service = QuoteService(db)
            quote = await q_service.create_quote(
                org_id=org.id,
                restaurant_id=rest.id,
                lead_id=lead.id,
                event_date=date(2026, 8, 1),
                guest_count=10,
                items=[{"name": "Past Event Item", "quantity": 10, "unit_price": 10.00}],
            )
            quote.status = "SENT"
            quote.expires_at = datetime.now(timezone.utc) - timedelta(days=1)
            await db.flush()

            expired = await q_service.check_expirations()
            assert len(expired) >= 1
            assert quote.status == "EXPIRED"

            await db.rollback()
        await engine.dispose()

    asyncio.run(_test())
