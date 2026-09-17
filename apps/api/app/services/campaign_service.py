from datetime import datetime, timezone
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.campaign import Campaign
from app.models.lead import Lead
from app.repositories.campaign_repo import CampaignRepository
from app.services.suppression_service import SuppressionService


class CampaignService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.repo = CampaignRepository(db)
        self.suppression_service = SuppressionService(db)

    async def create_campaign(self, org_id: str, **data) -> Campaign:
        return await self.repo.create(org_id, **data)

    async def get_campaign(self, campaign_id: str, org_id: str) -> Campaign | None:
        return await self.repo.get_by_id(campaign_id, org_id)

    async def list_campaigns(self, org_id: str) -> list[Campaign]:
        return await self.repo.list_by_org(org_id)

    async def start_campaign(self, campaign_id: str, org_id: str) -> Campaign:
        campaign = await self.repo.get_by_id(campaign_id, org_id)
        if not campaign:
            raise ValueError("Campaign not found")

        steps = await self.repo.get_steps(campaign_id)
        if not steps:
            raise ValueError("Campaign must have at least one step before starting")

        # Query eligible leads matching org and target filters
        stmt = select(Lead).where(Lead.organization_id == org_id)

        target_filters = campaign.target_filters or {}
        if "pipeline_status" in target_filters and target_filters["pipeline_status"]:
            stmt = stmt.where(Lead.pipeline_status.in_(target_filters["pipeline_status"]))
        if "priority" in target_filters and target_filters["priority"]:
            stmt = stmt.where(Lead.priority.in_(target_filters["priority"]))

        result = await self.db.execute(stmt)
        leads = result.scalars().all()

        now = datetime.now(timezone.utc)
        for lead in leads:
            if not lead.email:
                continue

            # Check suppression
            if await self.suppression_service.is_suppressed(org_id, lead.email):
                continue

            # Check existing campaign lead entry
            existing_cls = await self.repo.get_campaign_leads(campaign_id)
            existing_lead_ids = {cl.lead_id for cl in existing_cls}
            if lead.id not in existing_lead_ids:
                await self.repo.add_lead(campaign_id, lead.id, next_step_at=now)

        campaign.status = "ACTIVE"
        campaign.started_at = now
        await self.db.commit()
        await self.db.refresh(campaign)
        return campaign

    async def pause_campaign(self, campaign_id: str, org_id: str) -> Campaign:
        campaign = await self.repo.get_by_id(campaign_id, org_id)
        if not campaign:
            raise ValueError("Campaign not found")

        campaign.status = "PAUSED"
        await self.db.commit()
        await self.db.refresh(campaign)
        return campaign

    async def cancel_campaign(self, campaign_id: str, org_id: str) -> Campaign:
        campaign = await self.repo.get_by_id(campaign_id, org_id)
        if not campaign:
            raise ValueError("Campaign not found")

        campaign.status = "CANCELLED"
        campaign.completed_at = datetime.now(timezone.utc)
        await self.db.commit()
        await self.db.refresh(campaign)
        return campaign

    async def get_campaign_analytics(self, campaign_id: str, org_id: str) -> dict:
        campaign = await self.repo.get_by_id(campaign_id, org_id)
        if not campaign:
            raise ValueError("Campaign not found")

        cls = await self.repo.get_campaign_leads(campaign_id)
        counts = {
            "total_leads": len(cls),
            "pending": 0,
            "in_progress": 0,
            "completed": 0,
            "replied": 0,
            "bounced": 0,
            "unsubscribed": 0,
            "skipped": 0,
        }

        for cl in cls:
            status_key = cl.status.lower()
            if status_key in counts:
                counts[status_key] += 1

        return counts
