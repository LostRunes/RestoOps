from datetime import date, datetime
from decimal import Decimal
from pydantic import BaseModel, ConfigDict


class QuoteItemCreate(BaseModel):
    name: str
    description: str | None = None
    category: str | None = "FOOD"
    quantity: int = 1
    unit_price: Decimal = Decimal("0.00")


class QuoteItemResponse(BaseModel):
    id: str
    quote_id: str
    name: str
    description: str | None = None
    category: str | None = None
    quantity: int
    unit_price: Decimal
    total: Decimal
    sort_order: int
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class QuoteCreate(BaseModel):
    restaurant_id: str
    lead_id: str
    event_date: date
    guest_count: int
    event_type: str | None = None
    items: list[QuoteItemCreate] = []
    tax_rate: Decimal = Decimal("0.0000")
    delivery_fee: Decimal = Decimal("0.00")
    discount: Decimal = Decimal("0.00")
    notes: str | None = None
    terms: str | None = None
    valid_until: date | None = None
    conversation_id: str | None = None
    ai_run_id: str | None = None


class QuoteUpdate(BaseModel):
    event_date: date | None = None
    guest_count: int | None = None
    event_type: str | None = None
    tax_rate: Decimal | None = None
    delivery_fee: Decimal | None = None
    discount: Decimal | None = None
    notes: str | None = None
    terms: str | None = None
    valid_until: date | None = None


class QuoteResponse(BaseModel):
    id: str
    organization_id: str
    restaurant_id: str
    lead_id: str
    conversation_id: str | None = None
    ai_run_id: str | None = None
    quote_number: str
    event_date: date
    event_type: str | None = None
    guest_count: int
    subtotal: Decimal
    tax_rate: Decimal
    tax: Decimal
    delivery_fee: Decimal
    discount: Decimal
    total: Decimal
    notes: str | None = None
    terms: str | None = None
    status: str
    valid_until: date | None = None
    expires_at: datetime | None = None
    sent_at: datetime | None = None
    viewed_at: datetime | None = None
    accepted_at: datetime | None = None
    rejected_at: datetime | None = None
    created_by: str | None = None
    created_at: datetime
    updated_at: datetime
    items: list[QuoteItemResponse] = []

    model_config = ConfigDict(from_attributes=True)
