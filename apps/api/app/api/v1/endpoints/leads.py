"""
Lead management endpoints.

Provides:
    - Full CRUD for leads (org-scoped)
    - CSV bulk import (triggers Celery verification job)
    - Pipeline status updates
    - Lead activity timeline
    - Score recalculation
"""
from __future__ import annotations

import csv
import io
import re
from datetime import datetime, timezone
from typing import Optional
from uuid import uuid4

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.api.deps import get_current_user, get_db
from app.models.job import Job
from app.models.lead import Lead
from app.models.lead_activity import LeadActivity
from app.models.lead_contact import LeadContact
from app.models.lead_verification import LeadVerification
from app.models.user import User
from app.schemas.lead import (
    CSVImportResponse,
    LeadCreate,
    LeadListResponse,
    LeadResponse,
    LeadUpdate,
)
from app.schemas.verification import JobResponse

router = APIRouter(tags=["leads"])


EMAIL_REGEX = re.compile(r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$")

PIPELINE_STAGES = [
    "NEW", "VERIFIED", "CONTACTED", "INTERESTED",
    "QUALIFIED", "QUOTE_SENT", "NEGOTIATING", "WON", "LOST",
]


# ─── Helper ───────────────────────────────────────────────────────────────────

async def _get_org_lead(lead_id: str, org_id: str, db: AsyncSession) -> Lead:
    stmt = select(Lead).options(selectinload(Lead.contacts)).filter(
        Lead.id == lead_id, Lead.organization_id == org_id
    )
    result = await db.execute(stmt)
    lead = result.scalar_one_or_none()
    
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")
    return lead


def _log_activity(db: AsyncSession, lead_id: str, user_id: str | None,
                   activity_type: str, description: str, metadata: dict | None = None):
    act = LeadActivity(
        lead_id=lead_id,
        user_id=user_id,
        activity_type=activity_type,
        description=description,
        activity_metadata=metadata,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )
    db.add(act)


# ─── CRUD ─────────────────────────────────────────────────────────────────────

@router.post("/", response_model=LeadResponse, status_code=status.HTTP_201_CREATED)
async def create_lead(
    payload: LeadCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Create a single lead manually."""
    lead = Lead(
        id=str(uuid4()),
        organization_id=current_user.organization_id,
        restaurant_id=payload.restaurant_id,
        company_name=payload.company_name,
        contact_name=payload.contact_name,
        email=payload.email,
        phone=payload.phone,
        address=payload.address,
        industry=payload.industry,
        company_size=payload.company_size,
        source=payload.source,
        priority=payload.priority,
        pipeline_status=payload.pipeline_status,
        score=0,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )
    db.add(lead)
    await db.flush()

    for c in payload.contacts:
        contact = LeadContact(
            id=str(uuid4()),
            lead_id=lead.id,
            name=c.name,
            email=c.email,
            phone=c.phone,
            role=c.role,
            is_primary=c.is_primary,
        )
        db.add(contact)

    _log_activity(db, lead.id, current_user.id, "NOTE_ADDED", "Lead created manually.")
    await db.commit()
    return await _get_org_lead(lead.id, current_user.organization_id, db)


@router.get("/", response_model=LeadListResponse)
async def list_leads(
    page: int = Query(1, ge=1),
    size: int = Query(50, ge=1, le=200),
    pipeline_status: Optional[str] = Query(None),
    priority: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List leads for the current organization with filtering + pagination."""
    stmt = select(Lead).options(selectinload(Lead.contacts)).filter(Lead.organization_id == current_user.organization_id)

    if pipeline_status:
        stmt = stmt.filter(Lead.pipeline_status == pipeline_status.upper())
    if priority:
        stmt = stmt.filter(Lead.priority == priority.upper())
    if search:
        pattern = f"%{search}%"
        stmt = stmt.filter(
            Lead.company_name.ilike(pattern)
            | Lead.contact_name.ilike(pattern)
            | Lead.email.ilike(pattern)
        )

    # In async, counting requires a separate query but we can just fetch all for now or do a fast subquery count.
    # To keep it simple, we'll execute the paginated query and return it, while counting via another query.
    # We will use select(func.count(Lead.id)) for true count, but to avoid importing func, we will just count Python side if not paginated strictly, or we can use the same stmt.
    
    from sqlalchemy import func
    count_stmt = select(func.count(Lead.id)).select_from(stmt.subquery())
    count_result = await db.execute(count_stmt)
    total = count_result.scalar() or 0

    stmt = stmt.order_by(Lead.created_at.desc()).offset((page - 1) * size).limit(size)
    result = await db.execute(stmt)
    items = result.scalars().all()
    
    return {"items": items, "total": total, "page": page, "size": size}


@router.get("/{lead_id}", response_model=LeadResponse)
async def get_lead(
    lead_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await _get_org_lead(lead_id, current_user.organization_id, db)


@router.patch("/{lead_id}", response_model=LeadResponse)
async def update_lead(
    lead_id: str,
    payload: LeadUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    lead = await _get_org_lead(lead_id, current_user.organization_id, db)
    old_status = lead.pipeline_status

    for field, value in payload.model_dump(exclude_none=True).items():
        setattr(lead, field, value)
    lead.updated_at = datetime.now(timezone.utc)

    if payload.pipeline_status and payload.pipeline_status != old_status:
        _log_activity(
            db, lead.id, current_user.id, "STATUS_CHANGED",
            f"Pipeline moved: {old_status} → {payload.pipeline_status}",
            {"from": old_status, "to": payload.pipeline_status},
        )

    await db.commit()
    return await _get_org_lead(lead.id, current_user.organization_id, db)


@router.delete("/{lead_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_lead(
    lead_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    lead = await _get_org_lead(lead_id, current_user.organization_id, db)
    await db.delete(lead)
    await db.commit()


# ─── Pipeline Move ────────────────────────────────────────────────────────────

@router.post("/{lead_id}/pipeline/{stage}", response_model=LeadResponse)
async def move_pipeline(
    lead_id: str,
    stage: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Explicitly move a lead to a pipeline stage."""
    stage = stage.upper()
    if stage not in PIPELINE_STAGES:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid stage. Valid stages: {PIPELINE_STAGES}",
        )
    lead = await _get_org_lead(lead_id, current_user.organization_id, db)
    old_status = lead.pipeline_status
    lead.pipeline_status = stage
    lead.updated_at = datetime.now(timezone.utc)
    _log_activity(
        db, lead.id, current_user.id, "STATUS_CHANGED",
        f"Pipeline moved: {old_status} → {stage}",
        {"from": old_status, "to": stage},
    )
    await db.commit()
    return await _get_org_lead(lead.id, current_user.organization_id, db)


# ─── Activity Timeline ────────────────────────────────────────────────────────

@router.get("/{lead_id}/activity")
async def get_lead_activity(
    lead_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    lead = await _get_org_lead(lead_id, current_user.organization_id, db)
    stmt = select(LeadActivity).filter(LeadActivity.lead_id == lead.id).order_by(LeadActivity.created_at.desc())
    result = await db.execute(stmt)
    activities = result.scalars().all()
    
    return [
        {
            "id": a.id,
            "activity_type": a.activity_type,
            "description": a.description,
            "metadata": a.activity_metadata,
            "created_at": a.created_at,
        }
        for a in activities
    ]


# ─── Verification History ─────────────────────────────────────────────────────

@router.get("/{lead_id}/verifications")
async def get_lead_verifications(
    lead_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    lead = await _get_org_lead(lead_id, current_user.organization_id, db)
    stmt = select(LeadVerification).filter(LeadVerification.lead_id == lead.id).order_by(LeadVerification.checked_at.desc())
    result = await db.execute(stmt)
    verifications = result.scalars().all()
    
    return [
        {
            "id": v.id,
            "email": v.email,
            "status": v.status,
            "status_label": v.status_label,
            "score": v.score,
            "reason": v.reason,
            "provider": v.provider,
            "mx_host": v.mx_host,
            "latency_ms": v.latency_ms,
            "checked_at": v.checked_at,
        }
        for v in verifications
    ]


# ─── CSV Import ───────────────────────────────────────────────────────────────

@router.post("/import/csv", response_model=CSVImportResponse, status_code=status.HTTP_202_ACCEPTED)
async def import_csv(
    file: UploadFile = File(...),
    auto_verify: bool = Query(True, description="Auto-trigger email verification job after import"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Upload a CSV file to bulk-import leads.
    Supports headerless files (first row auto-detected if it contains '@').
    Optionally triggers a background verification job immediately after import.
    """
    if not file.filename.endswith(".csv"):
        raise HTTPException(status_code=400, detail="Only CSV files are supported")

    raw_content = await file.read()
    content_str = raw_content.decode("utf-8-sig")  # Handle BOM

    raw_rows = list(csv.reader(io.StringIO(content_str)))
    if not raw_rows:
        raise HTTPException(status_code=400, detail="Empty CSV file")

    # ── BounceBlitz headerless detection ──────────────────────────────────────
    first_cell = raw_rows[0][0].strip() if raw_rows[0] else ""
    has_header = "@" not in first_cell

    if has_header:
        reader = list(csv.DictReader(io.StringIO(content_str)))
    else:
        col_count = max(len(r) for r in raw_rows)
        synthetic_fields = ["email"] + [f"col{i}" for i in range(1, col_count)]
        reader = list(csv.DictReader(io.StringIO(content_str), fieldnames=synthetic_fields))

    if not reader:
        raise HTTPException(status_code=400, detail="No data rows found in CSV")

    # Detect email column
    first_row_keys = list(reader[0].keys())
    email_field = next(
        (f for f in first_row_keys if f.lower().strip() == "email"),
        first_row_keys[0],
    )

    # ── Import leads ──────────────────────────────────────────────────────────
    lead_ids: list[str] = []
    now = datetime.now(timezone.utc)

    for row in reader:
        email_raw = (row.get(email_field) or "").strip()
        email = email_raw if EMAIL_REGEX.match(email_raw) else None

        # Try to extract name from common column names
        contact_name = (
            row.get("name") or row.get("contact_name") or row.get("full_name") or None
        )
        company_name = row.get("company") or row.get("company_name") or None

        lead = Lead(
            id=str(uuid4()),
            organization_id=current_user.organization_id,
            email=email,
            contact_name=contact_name,
            company_name=company_name,
            source="CSV",
            pipeline_status="NEW",
            priority="MEDIUM",
            score=0,
            created_at=now,
            updated_at=now,
        )
        db.add(lead)
        await db.flush()
        lead_ids.append(lead.id)

        _log_activity(db, lead.id, current_user.id, "CSV_IMPORTED",
                      f"Lead imported from CSV: {file.filename}")

    await db.commit()

    # ── Optionally kick off a verification job ─────────────────────────────────
    job_id = str(uuid4())
    if auto_verify:
        job = Job(
            id=job_id,
            organization_id=current_user.organization_id,
            created_by_user_id=current_user.id,
            type="VERIFICATION",
            status="PENDING",
            total_items=len(lead_ids),
            processed_items=0,
            failed_items=0,
            result={"lead_ids": lead_ids},
            created_at=now,
            updated_at=now,
        )
        db.add(job)
        await db.commit()

        # Kick Celery task
        from app.jobs.verification_job import run_verification_job
        run_verification_job.delay(job_id)

    return {
        "job_id": job_id if auto_verify else "",
        "total_rows": len(lead_ids),
        "message": (
            f"Imported {len(lead_ids)} leads. Verification job queued: {job_id}"
            if auto_verify
            else f"Imported {len(lead_ids)} leads (no verification triggered)"
        ),
    }
