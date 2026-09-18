from typing import Any
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_db
from app.models.user import User
from app.schemas.quote import (
    QuoteCreate,
    QuoteItemCreate,
    QuoteItemResponse,
    QuoteResponse,
    QuoteUpdate,
)
from app.schemas.order import OrderResponse
from app.services.quote_service import QuoteService

router = APIRouter()


@router.post("", response_model=QuoteResponse, status_code=status.HTTP_201_CREATED)
async def create_quote(
    payload: QuoteCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Any:
    service = QuoteService(db)
    data = payload.model_dump()
    items = data.pop("items", [])
    data["items"] = items
    data["created_by"] = current_user.id
    quote = await service.create_quote(current_user.organization_id, **data)
    await db.commit()
    return quote


@router.get("", response_model=list[QuoteResponse])
async def list_quotes(
    lead_id: str | None = None,
    status_filter: str | None = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Any:
    service = QuoteService(db)
    return await service.list_quotes(
        current_user.organization_id, lead_id=lead_id, status=status_filter
    )


@router.get("/{quote_id}", response_model=QuoteResponse)
async def get_quote(
    quote_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Any:
    service = QuoteService(db)
    try:
        return await service.get_quote(quote_id, current_user.organization_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.patch("/{quote_id}", response_model=QuoteResponse)
async def update_quote(
    quote_id: str,
    payload: QuoteUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Any:
    service = QuoteService(db)
    try:
        res = await service.update_quote(
            quote_id, current_user.organization_id, **payload.model_dump(exclude_unset=True)
        )
        await db.commit()
        return res
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/{quote_id}/items", response_model=QuoteItemResponse)
async def add_quote_item(
    quote_id: str,
    payload: QuoteItemCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Any:
    service = QuoteService(db)
    try:
        res = await service.add_item(
            quote_id, current_user.organization_id, **payload.model_dump()
        )
        await db.commit()
        return res
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.delete("/{quote_id}/items/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_quote_item(
    quote_id: str,
    item_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> None:
    service = QuoteService(db)
    try:
        await service.remove_item(quote_id, current_user.organization_id, item_id)
        await db.commit()
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/{quote_id}/submit", response_model=QuoteResponse)
async def submit_quote(
    quote_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Any:
    service = QuoteService(db)
    try:
        res = await service.submit_for_approval(quote_id, current_user.organization_id)
        await db.commit()
        return res
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/{quote_id}/approve", response_model=QuoteResponse)
async def approve_quote(
    quote_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Any:
    service = QuoteService(db)
    try:
        res = await service.approve_quote(
            quote_id, current_user.organization_id, user_id=current_user.id
        )
        await db.commit()
        return res
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/{quote_id}/send", response_model=QuoteResponse)
async def send_quote(
    quote_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Any:
    service = QuoteService(db)
    try:
        res = await service.send_quote(
            quote_id, current_user.organization_id, user_id=current_user.id
        )
        await db.commit()
        return res
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/{quote_id}/accept", response_model=OrderResponse)
async def accept_quote(
    quote_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Any:
    service = QuoteService(db)
    try:
        order = await service.accept_quote(
            quote_id, current_user.organization_id, user_id=current_user.id
        )
        await db.commit()
        return order
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/{quote_id}/reject", response_model=QuoteResponse)
async def reject_quote(
    quote_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Any:
    service = QuoteService(db)
    try:
        res = await service.reject_quote(
            quote_id, current_user.organization_id, user_id=current_user.id
        )
        await db.commit()
        return res
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
