"""
AI API endpoints — conversation analysis, action approval, rejection, editing.
"""
from __future__ import annotations
from typing import Annotated, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.api.deps import get_current_user, get_current_tenant_org
from app.db.session import get_db
from app.models.user import User
from app.models.organization import Organization
from app.models.ai_run import AIRun
from app.models.ai_action import AIAction
from app.services.ai_service import AIService
from app.schemas.ai import (
    AIActionApproveRequest,
    AIActionRejectRequest,
    AIActionEditRequest,
    AIActionResponse,
    AIRunResponse,
    AIAnalysisResponse,
)
from app.core.logging import logger

router = APIRouter()


def _get_ai_service(db: AsyncSession) -> AIService:
    return AIService(db)


@router.get("/activity", response_model=list[AIRunResponse])
async def list_ai_activity(
    page: int = 1,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    org: Organization = Depends(get_current_tenant_org),
):
    """Paginated list of AI runs for the organization."""
    service = _get_ai_service(db)
    runs = await service.get_ai_activity(org.id, page=page)
    # Eager-load actions for each run
    result = []
    for run in runs:
        actions_res = await db.execute(
            select(AIAction).where(AIAction.ai_run_id == run.id).order_by(AIAction.created_at)
        )
        run_dict = {
            "id": run.id,
            "organization_id": run.organization_id,
            "agent": run.agent,
            "model": run.model,
            "conversation_id": run.conversation_id,
            "lead_id": run.lead_id,
            "structured_output": run.structured_output,
            "latency_ms": run.latency_ms,
            "tokens_used": run.tokens_used,
            "status": run.status,
            "error": run.error,
            "created_at": run.created_at,
            "actions": list(actions_res.scalars().all()),
        }
        result.append(AIRunResponse(**run_dict))
    return result


@router.get("/activity/{run_id}", response_model=AIRunResponse)
async def get_ai_run(
    run_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    org: Organization = Depends(get_current_tenant_org),
):
    """Get a single AI run with all its actions."""
    run_res = await db.execute(
        select(AIRun).where(AIRun.id == run_id, AIRun.organization_id == org.id)
    )
    run = run_res.scalar_one_or_none()
    if not run:
        raise HTTPException(status_code=404, detail="AI run not found")

    actions_res = await db.execute(
        select(AIAction).where(AIAction.ai_run_id == run.id).order_by(AIAction.created_at)
    )
    return AIRunResponse(
        id=run.id,
        organization_id=run.organization_id,
        agent=run.agent,
        model=run.model,
        conversation_id=run.conversation_id,
        lead_id=run.lead_id,
        structured_output=run.structured_output,
        latency_ms=run.latency_ms,
        tokens_used=run.tokens_used,
        status=run.status,
        error=run.error,
        created_at=run.created_at,
        actions=list(actions_res.scalars().all()),
    )


@router.get("/actions/pending", response_model=list[AIActionResponse])
async def list_pending_actions(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    org: Organization = Depends(get_current_tenant_org),
):
    """List all PROPOSED AI actions awaiting human approval."""
    service = _get_ai_service(db)
    actions = await service.list_pending_actions(org.id)
    return actions


@router.post("/actions/{action_id}/approve", response_model=dict)
async def approve_action(
    action_id: str,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    org: Organization = Depends(get_current_tenant_org),
):
    """Approve a PROPOSED AI action and execute it."""
    service = _get_ai_service(db)
    try:
        result = await service.approve_action(action_id, current_user.id, org.id)
        return result
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.post("/actions/{action_id}/reject", status_code=204)
async def reject_action(
    action_id: str,
    body: AIActionRejectRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    org: Organization = Depends(get_current_tenant_org),
):
    """Reject a PROPOSED AI action."""
    service = _get_ai_service(db)
    try:
        await service.reject_action(action_id, current_user.id, org.id, body.reason)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.post("/actions/{action_id}/edit", response_model=dict)
async def edit_and_approve_action(
    action_id: str,
    body: AIActionEditRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    org: Organization = Depends(get_current_tenant_org),
):
    """Edit action arguments and then approve + execute."""
    service = _get_ai_service(db)
    try:
        result = await service.edit_and_approve(
            action_id, current_user.id, org.id, body.new_arguments
        )
        return result
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.post("/analyze/{conversation_id}", response_model=AIAnalysisResponse)
async def trigger_analysis(
    conversation_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    org: Organization = Depends(get_current_tenant_org),
):
    """Manually trigger AI analysis on a conversation."""
    service = _get_ai_service(db)
    try:
        result = await service.analyze_conversation(conversation_id, org.id)
        return AIAnalysisResponse(**result)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except ConnectionError as exc:
        raise HTTPException(
            status_code=503,
            detail=f"Ollama AI service is not reachable. {str(exc)}",
        )
    except TimeoutError as exc:
        raise HTTPException(
            status_code=504,
            detail=f"AI analysis timed out. {str(exc)}",
        )
