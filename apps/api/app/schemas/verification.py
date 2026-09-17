from __future__ import annotations
from datetime import datetime
from typing import Optional
from pydantic import BaseModel


# ─── Single Email Verification ────────────────────────────────────────────────

class VerifyEmailRequest(BaseModel):
    email: str


class VerificationResultResponse(BaseModel):
    email: str
    status: str          # safe | role | catch_all | disposable | inbox_full | spamtrap | disabled | invalid | unknown
    status_label: str
    score: int
    reason: str
    meaning: str
    what_to_do: str

    syntax_valid: bool
    domain_valid: Optional[bool]
    mx_valid: Optional[bool]
    disposable: bool
    role_based: bool
    catch_all: bool
    spamtrap: bool

    mx_host: Optional[str]
    provider: Optional[str]
    latency_ms: Optional[int]


# ─── Batch Verification Job ───────────────────────────────────────────────────

class BatchVerifyRequest(BaseModel):
    lead_ids: list[str]


class BatchVerifyResponse(BaseModel):
    job_id: str
    total: int
    message: str


# ─── Job Status ───────────────────────────────────────────────────────────────

class JobResponse(BaseModel):
    id: str
    type: str
    status: str           # PENDING | RUNNING | COMPLETED | FAILED | CANCELLED
    total_items: int
    processed_items: int
    failed_items: int
    result: Optional[dict]
    error: Optional[str]
    started_at: Optional[datetime]
    completed_at: Optional[datetime]
    created_at: datetime

    model_config = {"from_attributes": True}


# ─── Suppression ──────────────────────────────────────────────────────────────

class SuppressionCreate(BaseModel):
    email: Optional[str] = None
    phone: Optional[str] = None
    reason: str = "MANUAL_BLOCK"
    source: str = "MANUAL"


class SuppressionResponse(BaseModel):
    id: str
    organization_id: str
    email: Optional[str]
    phone: Optional[str]
    reason: str
    source: str
    created_at: datetime

    model_config = {"from_attributes": True}
