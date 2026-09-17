"""
Celery task: batch email verification job.

Flow:
    1. Receive a job_id and list of lead_ids (or raw emails).
    2. Update job status → RUNNING in DB.
    3. Verify each email using the BounceBlitz engine (sync calls inside Celery worker).
    4. Write LeadVerification records, update Lead scores, log JobEvents.
    5. Auto-suppress confirmed invalid/disposable/spamtrap emails.
    6. Mark job COMPLETED (or FAILED on exception).
"""
from __future__ import annotations

import threading
import time
from datetime import datetime, timezone

from celery.utils.log import get_task_logger
from sqlalchemy.orm import Session

from app.jobs.celery_app import celery_app
from app.db.session import SessionLocal
from app.models.job import Job
from app.models.job_event import JobEvent
from app.models.lead import Lead
from app.models.lead_activity import LeadActivity
from app.models.lead_verification import LeadVerification
from app.models.suppression import SuppressionEntry
from app.services.verification.constants import STATUS_DETAILS
from app.services.verification.dns_checker import detect_provider, resolve_all_mx
from app.services.verification.engine import _verify_sync, DomainRateLimiter

logger = get_task_logger(__name__)

# Statuses that should be auto-suppressed
AUTO_SUPPRESS_STATUSES = {"invalid", "disposable", "spamtrap", "disabled"}


def _update_job_progress(db: Session, job: Job, processed: int, failed: int):
    job.processed_items = processed
    job.failed_items = failed
    db.commit()


def _add_event(db: Session, job_id: str, event_type: str, payload: dict | None = None):
    evt = JobEvent(
        job_id=job_id,
        event_type=event_type,
        payload=payload,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )
    db.add(evt)
    db.commit()


def _recalculate_lead_score(lead: Lead, verification_score: int) -> int:
    """
    Blend verification score with pipeline bonus:
        - base: verification score (0-100)
        - pipeline bonus: +5 for VERIFIED, +10 for QUALIFIED, +15 for WON
    """
    pipeline_bonus = {
        "VERIFIED": 5, "CONTACTED": 5, "INTERESTED": 8,
        "QUALIFIED": 10, "QUOTE_SENT": 12, "NEGOTIATING": 13, "WON": 15,
    }.get(lead.pipeline_status, 0)
    return min(100, verification_score + pipeline_bonus)


@celery_app.task(
    name="app.jobs.verification_job.run_verification_job",
    bind=True,
    max_retries=1,
    soft_time_limit=1800,  # 30 minutes max
)
def run_verification_job(self, job_id: str):
    """
    Celery task: verify all leads in a job and persist results.
    """
    db: Session = SessionLocal()
    mx_cache: dict = {}
    mx_lock = threading.Lock()
    rate_limiter = DomainRateLimiter(max_concurrent=2)

    try:
        # ── Load job ──────────────────────────────────────────────────────────
        job = db.query(Job).filter(Job.id == job_id).first()
        if not job:
            logger.error(f"Job {job_id} not found")
            return

        job.status = "RUNNING"
        job.started_at = datetime.now(timezone.utc)
        db.commit()
        _add_event(db, job_id, "STARTED", {"job_id": job_id})

        # ── Load leads from job result (lead_ids stored there) ────────────────
        lead_ids: list[str] = (job.result or {}).get("lead_ids", [])
        job.total_items = len(lead_ids)
        db.commit()

        if not lead_ids:
            job.status = "COMPLETED"
            job.completed_at = datetime.now(timezone.utc)
            job.result = {"message": "No leads to verify"}
            db.commit()
            return

        # ── Stats accumulators ────────────────────────────────────────────────
        stats = {s: 0 for s in STATUS_DETAILS}
        processed = 0
        failed = 0

        for lead_id in lead_ids:
            lead = db.query(Lead).filter(Lead.id == lead_id).first()
            if not lead or not lead.email:
                failed += 1
                _update_job_progress(db, job, processed, failed)
                continue

            try:
                result = _verify_sync(lead.email, mx_cache, mx_lock, rate_limiter)

                # ── Persist verification record ────────────────────────────────
                verification = LeadVerification(
                    lead_id=lead.id,
                    organization_id=lead.organization_id,
                    email=lead.email,
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
                    created_at=datetime.now(timezone.utc),
                    updated_at=datetime.now(timezone.utc),
                )
                db.add(verification)

                # ── Update lead score + pipeline ───────────────────────────────
                lead.score = _recalculate_lead_score(lead, result.score)
                if lead.pipeline_status == "NEW" and result.status in ("safe", "role", "catch_all"):
                    lead.pipeline_status = "VERIFIED"

                # ── Auto-suppress bad addresses ────────────────────────────────
                if result.status in AUTO_SUPPRESS_STATUSES:
                    existing = (
                        db.query(SuppressionEntry)
                        .filter(
                            SuppressionEntry.organization_id == lead.organization_id,
                            SuppressionEntry.email == lead.email,
                        )
                        .first()
                    )
                    if not existing:
                        suppress = SuppressionEntry(
                            organization_id=lead.organization_id,
                            email=lead.email,
                            reason=result.status.upper(),
                            source="SYSTEM",
                            created_at=datetime.now(timezone.utc),
                            updated_at=datetime.now(timezone.utc),
                        )
                        db.add(suppress)

                # ── Log activity ───────────────────────────────────────────────
                activity = LeadActivity(
                    lead_id=lead.id,
                    activity_type="VERIFIED",
                    description=f"Email verified: {result.status_label} (score: {result.score})",
                    metadata={
                        "status": result.status,
                        "score": result.score,
                        "reason": result.reason,
                        "provider": result.provider,
                        "latency_ms": result.latency_ms,
                    },
                    created_at=datetime.now(timezone.utc),
                    updated_at=datetime.now(timezone.utc),
                )
                db.add(activity)
                db.commit()

                stats[result.status] = stats.get(result.status, 0) + 1
                processed += 1

            except Exception as exc:
                logger.warning(f"Failed to verify lead {lead_id}: {exc}")
                db.rollback()
                failed += 1

            _update_job_progress(db, job, processed, failed)
            _add_event(db, job_id, "ITEM_PROCESSED", {
                "lead_id": lead_id,
                "email": lead.email if lead else None,
                "status": result.status if "result" in dir() else "error",
                "processed": processed,
                "total": len(lead_ids),
            })

        # ── Finalize job ──────────────────────────────────────────────────────
        job.status = "COMPLETED"
        job.completed_at = datetime.now(timezone.utc)
        job.result = {
            "stats": stats,
            "processed": processed,
            "failed": failed,
            "total": len(lead_ids),
        }
        db.commit()
        _add_event(db, job_id, "COMPLETED", job.result)
        logger.info(f"Verification job {job_id} completed: {stats}")

    except Exception as exc:
        logger.error(f"Verification job {job_id} failed: {exc}")
        try:
            job.status = "FAILED"
            job.error = str(exc)
            job.completed_at = datetime.now(timezone.utc)
            db.commit()
            _add_event(db, job_id, "FAILED", {"error": str(exc)})
        except Exception:
            pass
        raise

    finally:
        db.close()
