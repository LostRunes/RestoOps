from typing import Any
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_db
from app.models.user import User
from app.schemas.call import (
    CallCreateRequest,
    CallEndRequest,
    CallEventResponse,
    CallResponse,
    CallStatusResponse,
    StunServersResponse,
)
from app.services.call_service import CallService

router = APIRouter()


@router.post("", response_model=CallResponse, status_code=status.HTTP_201_CREATED)
async def start_call(
    payload: CallCreateRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Any:
    """
    Initiate a call to a lead via Exotel (phone) or WebRTC (browser).

    For Exotel:
    - `from_number`: agent's phone number (must be verified on trial)
    - `to`: lead's phone number (must be verified on trial)

    For WebRTC:
    - `from_number`: calling user_id
    - `to`: callee user_id
    - Returns a `exotel_call_sid` field containing the WebRTC room_id
    """
    service = CallService(db)
    try:
        call = await service.start_call(
            org_id=current_user.organization_id,
            lead_id=payload.lead_id,
            provider_type=payload.provider,
            from_identifier=payload.from_number,
            to_identifier=payload.to,
            initiated_by=current_user.id,
            restaurant_id=payload.restaurant_id,
            conversation_id=payload.conversation_id,
        )
        from sqlalchemy.orm import selectinload
        from sqlalchemy import select
        from app.models.call import Call
        stmt = select(Call).options(selectinload(Call.events)).where(Call.id == call.id)
        result = await db.execute(stmt)
        return result.scalar_one()
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("", response_model=list[CallResponse])
async def list_calls(
    lead_id: str | None = None,
    limit: int = 50,
    offset: int = 0,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Any:
    """List all calls for this organization, optionally filtered by lead."""
    service = CallService(db)
    return await service.list_calls(
        current_user.organization_id,
        lead_id=lead_id,
        limit=limit,
        offset=offset,
    )


@router.get("/stun-servers", response_model=StunServersResponse)
async def get_stun_servers(
    current_user: User = Depends(get_current_user),
) -> Any:
    """Return STUN server configuration for WebRTC ICE setup in the frontend."""
    return StunServersResponse(stun_servers=CallService.get_stun_servers())


@router.get("/{call_id}", response_model=CallResponse)
async def get_call(
    call_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Any:
    service = CallService(db)
    try:
        return await service.get_call(call_id, current_user.organization_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post("/{call_id}/end", response_model=CallResponse)
async def end_call(
    call_id: str,
    payload: CallEndRequest | None = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Any:
    """
    Cancel/end an active call.
    Note: For Exotel trial, this marks the call CANCELLED in our DB.
    Exotel will still deliver a terminal status webhook when the call actually ends.
    """
    service = CallService(db)
    try:
        return await service.end_call(call_id, current_user.organization_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/{call_id}/status", response_model=CallStatusResponse)
async def get_call_status(
    call_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Any:
    service = CallService(db)
    try:
        call = await service.get_call(call_id, current_user.organization_id)
        return CallStatusResponse(
            call_id=call.id,
            status=call.status,
            provider=call.provider,
            duration_seconds=call.duration_seconds,
            exotel_call_sid=call.exotel_call_sid,
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get("/{call_id}/events", response_model=list[CallEventResponse])
async def get_call_events(
    call_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Any:
    service = CallService(db)
    try:
        return await service.get_events(call_id, current_user.organization_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
