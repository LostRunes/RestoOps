from datetime import date
from typing import Any
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_db
from app.models.user import User
from app.schemas.order import OrderResponse, OrderStatusUpdate, RevenueResponse
from app.services.order_service import OrderService

router = APIRouter()


@router.get("", response_model=list[OrderResponse])
async def list_orders(
    lead_id: str | None = None,
    status_filter: str | None = Query(None, alias="status"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Any:
    service = OrderService(db)
    return await service.list_orders(
        current_user.organization_id, lead_id=lead_id, status=status_filter
    )


@router.get("/revenue", response_model=RevenueResponse)
async def get_revenue_stats(
    start_date: date | None = None,
    end_date: date | None = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Any:
    service = OrderService(db)
    return await service.get_revenue(
        current_user.organization_id, start_date=start_date, end_date=end_date
    )


@router.get("/{order_id}", response_model=OrderResponse)
async def get_order(
    order_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Any:
    service = OrderService(db)
    try:
        return await service.get_order(order_id, current_user.organization_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.patch("/{order_id}/status", response_model=OrderResponse)
async def update_order_status(
    order_id: str,
    payload: OrderStatusUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Any:
    service = OrderService(db)
    try:
        return await service.update_status(
            order_id,
            current_user.organization_id,
            new_status=payload.status,
            user_id=current_user.id,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
