from datetime import datetime, timezone
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from app.models.campaign import Campaign
from app.models.campaign_lead import CampaignLead
from app.models.campaign_step import CampaignStep


class CampaignRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(self, org_id: str, **data) -> Campaign:
        steps_data = data.pop("steps", [])
        campaign = Campaign(organization_id=org_id, **data)
        self.db.add(campaign)
        await self.db.flush()

        for step_idx, step_info in enumerate(steps_data, start=1):
            step = CampaignStep(
                campaign_id=campaign.id,
                step_number=step_info.get("step_number", step_idx),
                step_type=step_info.get("step_type", "EMAIL"),
                delay_days=step_info.get("delay_days", 0),
                subject=step_info.get("subject"),
                body=step_info.get("body"),
            )
            self.db.add(step)

        await self.db.commit()
        await self.db.refresh(campaign)
        return campaign

    async def get_by_id(self, campaign_id: str, org_id: str) -> Campaign | None:
        stmt = (
            select(Campaign)
            .options(
                selectinload(Campaign.steps),
                selectinload(Campaign.campaign_leads),
            )
            .where(Campaign.id == campaign_id, Campaign.organization_id == org_id)
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def list_by_org(self, org_id: str) -> list[Campaign]:
        stmt = (
            select(Campaign)
            .options(selectinload(Campaign.steps))
            .where(Campaign.organization_id == org_id)
            .order_by(Campaign.created_at.desc())
        )
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def update(self, campaign_id: str, org_id: str, **data) -> Campaign | None:
        campaign = await self.get_by_id(campaign_id, org_id)
        if not campaign:
            return None

        for key, val in data.items():
            if hasattr(campaign, key) and val is not None:
                setattr(campaign, key, val)

        await self.db.commit()
        await self.db.refresh(campaign)
        return campaign

    async def add_step(self, campaign_id: str, **step_data) -> CampaignStep:
        step = CampaignStep(campaign_id=campaign_id, **step_data)
        self.db.add(step)
        await self.db.commit()
        await self.db.refresh(step)
        return step

    async def get_steps(self, campaign_id: str) -> list[CampaignStep]:
        stmt = (
            select(CampaignStep)
            .where(CampaignStep.campaign_id == campaign_id)
            .order_by(CampaignStep.step_number.asc())
        )
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def add_lead(self, campaign_id: str, lead_id: str, next_step_at: datetime | None = None) -> CampaignLead:
        cl = CampaignLead(
            campaign_id=campaign_id,
            lead_id=lead_id,
            current_step=0,
            status="PENDING",
            next_step_at=next_step_at or datetime.now(timezone.utc),
        )
        self.db.add(cl)
        await self.db.commit()
        await self.db.refresh(cl)
        return cl

    async def get_campaign_leads(self, campaign_id: str, status: str | None = None) -> list[CampaignLead]:
        stmt = select(CampaignLead).options(selectinload(CampaignLead.lead)).where(CampaignLead.campaign_id == campaign_id)
        if status:
            stmt = stmt.where(CampaignLead.status == status)
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def get_due_leads(self, campaign_id: str) -> list[CampaignLead]:
        now = datetime.now(timezone.utc)
        stmt = (
            select(CampaignLead)
            .options(selectinload(CampaignLead.lead))
            .where(
                CampaignLead.campaign_id == campaign_id,
                CampaignLead.status.in_(["PENDING", "IN_PROGRESS"]),
                CampaignLead.next_step_at <= now,
            )
        )
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def update_campaign_lead(self, cl_id: str, **data) -> None:
        stmt = update(CampaignLead).where(CampaignLead.id == cl_id).values(**data)
        await self.db.execute(stmt)
        await self.db.commit()
