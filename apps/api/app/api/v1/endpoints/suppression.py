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
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db
from app.models.suppression import SuppressionEntry
from app.models.user import User
from app.schemas.verification import SuppressionCreate, SuppressionResponse

router = APIRouter(prefix="/suppression", tags=["suppression"])


@router.get("/", response_model=list[SuppressionResponse])
def list_suppressed(
    page: int = Query(1, ge=1),
    size: int = Query(100, ge=1, le=500),
    reason: str | None = Query(None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    q = db.query(SuppressionEntry).filter(
        SuppressionEntry.organization_id == current_user.organization_id
    )
    if reason:
        q = q.filter(SuppressionEntry.reason == reason.upper())
    return q.order_by(SuppressionEntry.created_at.desc()).offset((page - 1) * size).limit(size).all()


@router.post("/", response_model=SuppressionResponse, status_code=status.HTTP_201_CREATED)
def add_suppression(
    payload: SuppressionCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if not payload.email and not payload.phone:
        raise HTTPException(status_code=400, detail="Email or phone is required")

    if payload.email:
        existing = db.query(SuppressionEntry).filter(
            SuppressionEntry.organization_id == current_user.organization_id,
            SuppressionEntry.email == payload.email,
        ).first()
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
    db.commit()
    db.refresh(entry)
    return entry


@router.delete("/{entry_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_suppression(
    entry_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    entry = db.query(SuppressionEntry).filter(
        SuppressionEntry.id == entry_id,
        SuppressionEntry.organization_id == current_user.organization_id,
    ).first()
    if not entry:
        raise HTTPException(status_code=404, detail="Suppression entry not found")
    db.delete(entry)
    db.commit()


@router.post("/check")
def check_suppressed(
    payload: dict,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Check if an email or phone is on the suppression list."""
    email = payload.get("email")
    phone = payload.get("phone")

    q = db.query(SuppressionEntry).filter(
        SuppressionEntry.organization_id == current_user.organization_id
    )
    if email:
        entry = q.filter(SuppressionEntry.email == email).first()
        if entry:
            return {"suppressed": True, "reason": entry.reason, "source": entry.source}
    if phone:
        entry = q.filter(SuppressionEntry.phone == phone).first()
        if entry:
            return {"suppressed": True, "reason": entry.reason, "source": entry.source}

    return {"suppressed": False}
