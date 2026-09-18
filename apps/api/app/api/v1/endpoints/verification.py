"""
Email verification endpoints.

Provides:
    - Single email real-time verification (BounceBlitz engine)
    - Batch verification job trigger (Celery)
    - Job status polling
    - Job cancellation
"""
from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.api.deps import get_current_user, get_db
from app.models.job import Job
from app.models.lead import Lead
from app.models.lead_verification import LeadVerification
from app.models.user import User
from app.schemas.verification import (
    BatchVerifyRequest,
    BatchVerifyResponse,
    JobResponse,
    VerificationResultResponse,
    VerifyEmailRequest,
)
from app.services.verification import verify_email

router = APIRouter(tags=["verification"])



# ─── Single Email Verification (Real-time) ────────────────────────────────────

@router.post("/check", response_model=VerificationResultResponse)
async def verify_single_email(
    payload: VerifyEmailRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Verify a single email address in real-time using the BounceBlitz engine.
    Returns the 9-status result with score, reasoning, and granular checks.
    """
    result = await verify_email(payload.email)

    # Persist the verification record (no lead_id — standalone check)
    record = LeadVerification(
        id=str(uuid4()),
        lead_id=None,
        organization_id=current_user.organization_id,
        email=result.email,
        status=result.status,
        status_label=result.status_label,
        score=result.score,
        reason=result.reason,
        syntax_valid=result.syntax_valid,
        domain_valid=result.domain_valid,
        mx_valid=result.mx_valid,
        disposable=result.disposable,
        role_based=result.role_based,
        catch_all=result.catch_all,
        spamtrap=result.spamtrap,
        smtp_code=result.smtp_code,
        smtp_message=result.smtp_message,
        mx_host=result.mx_host,
        provider=result.provider,
        latency_ms=result.latency_ms,
        checked_at=datetime.now(timezone.utc),
    )
    db.add(record)
    await db.commit()

    return VerificationResultResponse(
        email=result.email,
        status=result.status,
        status_label=result.status_label,
        score=result.score,
        reason=result.reason,
        meaning=result.meaning,
        what_to_do=result.what_to_do,
        syntax_valid=result.syntax_valid,
        domain_valid=result.domain_valid,
        mx_valid=result.mx_valid,
        disposable=result.disposable,
        role_based=result.role_based,
        catch_all=result.catch_all,
        spamtrap=result.spamtrap,
        mx_host=result.mx_host,
        provider=result.provider,
        latency_ms=result.latency_ms,
    )


# ─── Batch Verification (Celery Job) ─────────────────────────────────────────

@router.post("/batch", response_model=BatchVerifyResponse, status_code=status.HTTP_202_ACCEPTED)
async def trigger_batch_verification(
    payload: BatchVerifyRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Enqueue a batch verification job for the given list of lead IDs.
    Returns a job_id for progress polling.
    """
    if not payload.lead_ids:
        raise HTTPException(status_code=400, detail="lead_ids must not be empty")

    # Validate all lead IDs belong to this org
    stmt = select(Lead).filter(
        Lead.id.in_(payload.lead_ids),
        Lead.organization_id == current_user.organization_id,
    )
    result = await db.execute(stmt)
    leads = result.scalars().all()
    
    found_ids = {l.id for l in leads}
    missing = set(payload.lead_ids) - found_ids
    if missing:
        raise HTTPException(
            status_code=404,
            detail=f"Leads not found: {list(missing)[:5]}{'...' if len(missing) > 5 else ''}",
        )

    now = datetime.now(timezone.utc)
    job_id = str(uuid4())
    job = Job(
        id=job_id,
        organization_id=current_user.organization_id,
        created_by_user_id=current_user.id,
        type="VERIFICATION",
        status="PENDING",
        total_items=len(payload.lead_ids),
        processed_items=0,
        failed_items=0,
        result={"lead_ids": payload.lead_ids},
        created_at=now,
        updated_at=now,
    )
    db.add(job)
    await db.commit()

    from app.jobs.verification_job import run_verification_job
    run_verification_job.delay(job_id)

    return {"job_id": job_id, "total": len(payload.lead_ids), "message": "Verification job queued"}


# ─── Job Status Polling ────────────────────────────────────────────────────────

@router.get("/jobs/{job_id}", response_model=JobResponse)
async def get_job_status(
    job_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Poll a verification job for real-time progress."""
    stmt = select(Job).filter(
        Job.id == job_id,
        Job.organization_id == current_user.organization_id,
    )
    result = await db.execute(stmt)
    job = result.scalar_one_or_none()
    
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return job


@router.get("/jobs", response_model=list[JobResponse])
async def list_jobs(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List recent verification jobs for this organization."""
    stmt = select(Job).filter(
        Job.organization_id == current_user.organization_id,
        Job.type == "VERIFICATION",
    ).order_by(Job.created_at.desc()).limit(50)
    
    result = await db.execute(stmt)
    jobs = result.scalars().all()
    return jobs


# ─── Job Cancellation ─────────────────────────────────────────────────────────

@router.post("/jobs/{job_id}/cancel", response_model=JobResponse)
async def cancel_job(
    job_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Cancel a pending or running verification job."""
    stmt = select(Job).filter(
        Job.id == job_id,
        Job.organization_id == current_user.organization_id,
    )
    result = await db.execute(stmt)
    job = result.scalar_one_or_none()
    
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    if job.status in ("COMPLETED", "FAILED", "CANCELLED"):
        raise HTTPException(status_code=400, detail=f"Job is already {job.status}")

    job.status = "CANCELLED"
    job.completed_at = datetime.now(timezone.utc)
    job.updated_at = datetime.now(timezone.utc)
    await db.commit()
    await db.refresh(job)
    return job
