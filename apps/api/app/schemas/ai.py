"""
Pydantic schemas for AI API endpoints.
"""
from __future__ import annotations
from datetime import datetime
from typing import Any, Optional
from pydantic import BaseModel


# ── Request schemas ─────────────────────────────────────────────────────────

class AIActionApproveRequest(BaseModel):
    """Empty body — just POST to approve."""
    pass


class AIActionRejectRequest(BaseModel):
    reason: str


class AIActionEditRequest(BaseModel):
    new_arguments: dict[str, Any]


# ── Response schemas ─────────────────────────────────────────────────────────

class AIActionResponse(BaseModel):
    id: str
    ai_run_id: str
    organization_id: str
    tool: str
    arguments: dict[str, Any]
    result: Optional[dict[str, Any]] = None
    status: str
    approved_by: Optional[str] = None
    approved_at: Optional[datetime] = None
    executed_at: Optional[datetime] = None
    rejection_reason: Optional[str] = None
    created_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class AIRunResponse(BaseModel):
    id: str
    organization_id: str
    agent: str
    model: str
    conversation_id: Optional[str] = None
    lead_id: Optional[str] = None
    structured_output: Optional[dict[str, Any]] = None
    latency_ms: int
    tokens_used: Optional[int] = None
    status: str
    error: Optional[str] = None
    created_at: Optional[datetime] = None
    actions: list[AIActionResponse] = []

    model_config = {"from_attributes": True}


class AIAnalysisResponse(BaseModel):
    ai_run_id: str
    status: str
    analysis: Optional[dict[str, Any]] = None
    actions_proposed: int
