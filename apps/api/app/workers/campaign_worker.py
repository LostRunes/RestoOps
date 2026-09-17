import asyncio
from datetime import datetime, timedelta, timezone
from sqlalchemy import select

from app.db.session import AsyncSessionLocal
from app.jobs.celery_app import celery_app
from app.models.campaign import Campaign
from app.models.lead_activity import LeadActivity
from app.repositories.campaign_repo import CampaignRepository
from app.repositories.conversation_repo import ConversationRepository
from app.repositories.message_repo import MessageRepository
from app.services.email_service import EmailService
from app.services.suppression_service import SuppressionService


async def _async_execute_campaign_step(campaign_id: str, org_id: str):
    async with AsyncSessionLocal() as db:
        repo = CampaignRepository(db)
        conv_repo = ConversationRepository(db)
        msg_repo = MessageRepository(db)
        email_service = EmailService()
        suppression_service = SuppressionService(db)

        campaign = await repo.get_by_id(campaign_id, org_id)
        if not campaign or campaign.status != "ACTIVE":
            return

        steps = await repo.get_steps(campaign_id)
        if not steps:
            return

        steps_map = {step.step_number: step for step in steps}
        due_leads = await repo.get_due_leads(campaign_id)

        for cl in due_leads:
            next_step_num = cl.current_step + 1
            step = steps_map.get(next_step_num)
            if not step:
                await repo.update_campaign_lead(cl.id, status="COMPLETED", next_step_at=None)
                continue

            lead = cl.lead
            if not lead or not lead.email:
                await repo.update_campaign_lead(cl.id, status="SKIPPED")
                continue

            if await suppression_service.is_suppressed(org_id, lead.email):
                await repo.update_campaign_lead(cl.id, status="UNSUBSCRIBED")
                continue

            res = await email_service.send_campaign_email(lead=lead, step=step, campaign=campaign)
            if res.success:
                conv = await conv_repo.get_by_lead(lead.id, org_id, channel="EMAIL")
                if not conv:
                    conv = await conv_repo.create(
                        org_id=org_id,
                        lead_id=lead.id,
                        channel="EMAIL",
                        subject=step.subject,
                    )

                await msg_repo.create(
                    conversation_id=conv.id,
                    direction="OUTBOUND",
                    sender=getattr(email_service.provider, "default_from_addr", "noreply@restoops.local"),
                    recipient=lead.email,
                    subject=step.subject,
                    body=step.body or "",
                    message_id=res.message_id,
                    status="SENT",
                )

                activity = LeadActivity(
                    lead_id=lead.id,
                    activity_type="EMAIL_SENT",
                    description=f"Campaign '{campaign.name}' Step #{step.step_number} sent",
                    activity_metadata={"campaign_id": campaign.id, "step_number": step.step_number},
                )
                db.add(activity)

                if lead.pipeline_status in ["NEW", "VERIFIED"]:
                    lead.pipeline_status = "CONTACTED"

                now = datetime.now(timezone.utc)
                has_next = (next_step_num + 1) in steps_map
                next_step_at = (now + timedelta(days=step.delay_days)) if has_next else None
                new_status = "IN_PROGRESS" if has_next else "COMPLETED"

                await repo.update_campaign_lead(
                    cl.id,
                    current_step=next_step_num,
                    status=new_status,
                    next_step_at=next_step_at,
                )
                await db.commit()
            else:
                await repo.update_campaign_lead(cl.id, status="BOUNCED")


async def _async_check_due_steps():
    async with AsyncSessionLocal() as db:
        stmt = select(Campaign).where(Campaign.status == "ACTIVE")
        result = await db.execute(stmt)
        active_campaigns = result.scalars().all()

        for c in active_campaigns:
            await _async_execute_campaign_step(c.id, c.organization_id)


@celery_app.task(name="app.workers.campaign_worker.execute_campaign_step", bind=True, max_retries=3)
def execute_campaign_step(self, campaign_id: str, org_id: str):
    asyncio.run(_async_execute_campaign_step(campaign_id, org_id))


@celery_app.task(name="app.workers.campaign_worker.check_due_steps")
def check_due_steps():
    asyncio.run(_async_check_due_steps())
