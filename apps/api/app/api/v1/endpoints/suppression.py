"""
Suppression list endpoints.

An org-scoped blocklist. Any email/phone on this list must not be contacted.
Populated automatically by the verification engine for invalid/disposable/spamtrap emails,
and manually by users via these endpoints.
"""
from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.api.deps import get_current_user, get_db
from app.models.suppression import SuppressionEntry
from app.models.user import User
from app.schemas.verification import SuppressionCreate, SuppressionResponse

router = APIRouter(tags=["suppression"])

@router.get("/", response_model=list[SuppressionResponse])
async def list_suppressed(
    page: int = Query(1, ge=1),
    size: int = Query(100, ge=1, le=500),
    reason: str | None = Query(None),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    stmt = select(SuppressionEntry).filter(
        SuppressionEntry.organization_id == current_user.organization_id
    )
    if reason:
        stmt = stmt.filter(SuppressionEntry.reason == reason.upper())
    stmt = stmt.order_by(SuppressionEntry.created_at.desc()).offset((page - 1) * size).limit(size)
    result = await db.execute(stmt)
    return result.scalars().all()


@router.post("/", response_model=SuppressionResponse, status_code=status.HTTP_201_CREATED)
async def add_suppression(
    payload: SuppressionCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if not payload.email and not payload.phone:
        raise HTTPException(status_code=400, detail="Email or phone is required")

    if payload.email:
        stmt = select(SuppressionEntry).filter(
            SuppressionEntry.organization_id == current_user.organization_id,
            SuppressionEntry.email == payload.email,
        )
        result = await db.execute(stmt)
        existing = result.scalar_one_or_none()
        if existing:
            raise HTTPException(status_code=409, detail="Email already in suppression list")

    now = datetime.now(timezone.utc)
    entry = SuppressionEntry(
        id=str(uuid4()),
        organization_id=current_user.organization_id,
        email=payload.email,
        phone=payload.phone,
        reason=payload.reason.upper(),
        source=payload.source.upper(),
        created_at=now,
        updated_at=now,
    )
    db.add(entry)
    await db.commit()
    await db.refresh(entry)
    return entry


@router.delete("/{entry_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_suppression(
    entry_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    stmt = select(SuppressionEntry).filter(
        SuppressionEntry.id == entry_id,
        SuppressionEntry.organization_id == current_user.organization_id,
    )
    result = await db.execute(stmt)
    entry = result.scalar_one_or_none()
    
    if not entry:
        raise HTTPException(status_code=404, detail="Suppression entry not found")
    await db.delete(entry)
    await db.commit()


@router.post("/check")
async def check_suppressed(
    payload: dict,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Check if an email or phone is on the suppression list."""
    email = payload.get("email")
    phone = payload.get("phone")

    stmt = select(SuppressionEntry).filter(
        SuppressionEntry.organization_id == current_user.organization_id
    )
    
    if email:
        result = await db.execute(stmt.filter(SuppressionEntry.email == email))
        entry = result.scalar_one_or_none()
        if entry:
            return {"suppressed": True, "reason": entry.reason, "source": entry.source}
            
    if phone:
        result = await db.execute(stmt.filter(SuppressionEntry.phone == phone))
        entry = result.scalar_one_or_none()
        if entry:
            return {"suppressed": True, "reason": entry.reason, "source": entry.source}

    return {"suppressed": False}
