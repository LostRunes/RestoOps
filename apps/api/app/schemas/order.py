from datetime import date, datetime
from decimal import Decimal
from pydantic import BaseModel, ConfigDict


class OrderItemResponse(BaseModel):
    id: str
    order_id: str
    name: str
    description: str | None = None
    quantity: int
    unit_price: Decimal
    total: Decimal
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class OrderResponse(BaseModel):
    id: str
    organization_id: str
    restaurant_id: str
    lead_id: str
    quote_id: str
    order_number: str
    event_date: date
    guest_count: int
    total: Decimal
    status: str
    special_instructions: str | None = None
    confirmed_at: datetime | None = None
    completed_at: datetime | None = None
    cancelled_at: datetime | None = None
    created_at: datetime
    updated_at: datetime
    items: list[OrderItemResponse] = []

    model_config = ConfigDict(from_attributes=True)


class OrderStatusUpdate(BaseModel):
    status: str


class MonthlyRevenue(BaseModel):
    month: str
    revenue: Decimal


class RevenueResponse(BaseModel):
    total_revenue: Decimal
    order_count: int
    average_order_value: Decimal
    by_status: dict[str, Decimal]
    by_month: list[MonthlyRevenue]
