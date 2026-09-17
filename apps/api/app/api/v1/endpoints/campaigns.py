from typing import Any
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_db
from app.models.user import User
from app.schemas.campaign import (
    CampaignAnalyticsResponse,
    CampaignCreate,
    CampaignLeadResponse,
    CampaignResponse,
    CampaignUpdate,
)
from app.services.campaign_service import CampaignService
from app.workers.campaign_worker import execute_campaign_step

router = APIRouter()


@router.post("", response_model=CampaignResponse, status_code=status.HTTP_201_CREATED)
async def create_campaign(
    payload: CampaignCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Any:
    service = CampaignService(db)
    data = payload.model_dump()
    data["created_by"] = current_user.id
    campaign = await service.create_campaign(current_user.organization_id, **data)
    return campaign


@router.get("", response_model=list[CampaignResponse])
async def list_campaigns(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Any:
    service = CampaignService(db)
    return await service.list_campaigns(current_user.organization_id)


@router.get("/{campaign_id}", response_model=CampaignResponse)
async def get_campaign(
    campaign_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Any:
    service = CampaignService(db)
    campaign = await service.get_campaign(campaign_id, current_user.organization_id)
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")
    return campaign


@router.patch("/{campaign_id}", response_model=CampaignResponse)
async def update_campaign(
    campaign_id: str,
    payload: CampaignUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Any:
    service = CampaignService(db)
    campaign = await service.repo.update(
        campaign_id, current_user.organization_id, **payload.model_dump(exclude_unset=True)
    )
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")
    return campaign


@router.post("/{campaign_id}/start", response_model=CampaignResponse)
async def start_campaign(
    campaign_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Any:
    service = CampaignService(db)
    try:
        campaign = await service.start_campaign(campaign_id, current_user.organization_id)
        # Trigger celery step execution
        execute_campaign_step.delay(campaign.id, current_user.organization_id)
        return campaign
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/{campaign_id}/pause", response_model=CampaignResponse)
async def pause_campaign(
    campaign_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Any:
    service = CampaignService(db)
    try:
        return await service.pause_campaign(campaign_id, current_user.organization_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/{campaign_id}/cancel", response_model=CampaignResponse)
async def cancel_campaign(
    campaign_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Any:
    service = CampaignService(db)
    try:
        return await service.cancel_campaign(campaign_id, current_user.organization_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/{campaign_id}/leads", response_model=list[CampaignLeadResponse])
async def list_campaign_leads(
    campaign_id: str,
    status_filter: str | None = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Any:
    service = CampaignService(db)
    campaign = await service.get_campaign(campaign_id, current_user.organization_id)
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")

    cls = await service.repo.get_campaign_leads(campaign_id, status=status_filter)
    res = []
    for cl in cls:
        item = CampaignLeadResponse.model_validate(cl)
        if cl.lead:
            item.lead_email = cl.lead.email
            item.lead_contact_name = cl.lead.contact_name
        res.append(item)
    return res


@router.get("/{campaign_id}/analytics", response_model=CampaignAnalyticsResponse)
async def get_campaign_analytics(
    campaign_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Any:
    service = CampaignService(db)
    try:
        analytics = await service.get_campaign_analytics(campaign_id, current_user.organization_id)
        return CampaignAnalyticsResponse(**analytics)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
