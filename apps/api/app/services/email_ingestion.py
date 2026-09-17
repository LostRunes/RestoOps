from datetime import datetime, timezone
import re
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.integrations.email.base import EmailProvider
from app.integrations.email.mailpit import MailpitProvider
from app.models.campaign_lead import CampaignLead
from app.models.lead import Lead
from app.models.lead_activity import LeadActivity
from app.models.organization import Organization
from app.repositories.conversation_repo import ConversationRepository
from app.repositories.message_repo import MessageRepository
from app.services.conversation_matcher import ConversationMatcher


class EmailIngestionService:
    def __init__(self, db: AsyncSession, provider: EmailProvider | None = None):
        self.db = db
        self.provider = provider or MailpitProvider()
        self.matcher = ConversationMatcher(db)
        self.conv_repo = ConversationRepository(db)
        self.msg_repo = MessageRepository(db)

    def _extract_email(self, addr_str: str) -> str:
        if not addr_str:
            return ""
        match = re.search(r"[\w\.-]+@[\w\.-]+\.\w+", addr_str)
        return match.group(0).lower() if match else addr_str.strip().lower()

    async def ingest_new_messages(self, org_id: str | None = None) -> int:
        if not org_id:
            # Fallback to default first organization if org_id not passed
            stmt = select(Organization).limit(1)
            result = await self.db.execute(stmt)
            org = result.scalar_one_or_none()
            if not org:
                return 0
            org_id = org.id

        raw_messages = await self.provider.fetch_new_messages()
        ingested_count = 0

        for raw_msg in raw_messages:
            sender_raw = raw_msg.get("From", {})
            sender_addr = sender_raw.get("Address", "") if isinstance(sender_raw, dict) else str(sender_raw)
            sender_email = self._extract_email(sender_addr)

            # Skip system generated or self-sent if sender is default system email
            to_raw = raw_msg.get("To", [])
            recipient_str = to_raw[0].get("Address", "") if (isinstance(to_raw, list) and to_raw and isinstance(to_raw[0], dict)) else str(to_raw)
            recipient_email = self._extract_email(recipient_str)

            message_id = raw_msg.get("ID") or raw_msg.get("MessageID") or ""
            # Check if message was already ingested
            if message_id:
                existing_msg = await self.msg_repo.get_by_message_id(message_id)
                if existing_msg:
                    continue

            subject = raw_msg.get("Subject", "")
            body = raw_msg.get("Text", "") or raw_msg.get("HTML", "") or ""

            headers = raw_msg.get("Headers", {})
            if isinstance(headers, dict):
                normalized_headers = {k: (v[0] if isinstance(v, list) else v) for k, v in headers.items()}
            else:
                normalized_headers = {}

            # Match conversation
            conv = await self.matcher.match(
                message_headers=normalized_headers,
                org_id=org_id,
                sender_email=sender_email,
                subject=subject,
            )

            # Store message
            message_record = await self.msg_repo.create(
                conversation_id=conv.id,
                direction="INBOUND",
                sender=sender_email,
                recipient=recipient_email,
                subject=subject,
                body=body,
                message_id=message_id,
                in_reply_to=normalized_headers.get("In-Reply-To"),
                references=normalized_headers.get("References"),
                status="RECEIVED",
            )

            now = datetime.now(timezone.utc)
            # Update conversation metadata
            await self.conv_repo.update(
                conv.id,
                message_count=conv.message_count + 1,
                last_message_at=now,
                updated_at=now,
            )

            # Log Lead Activity & update Campaign Lead status if applicable
            lead_stmt = select(Lead).where(Lead.id == conv.lead_id)
            lead_res = await self.db.execute(lead_stmt)
            lead = lead_res.scalar_one_or_none()

            if lead:
                # Log lead activity
                activity = LeadActivity(
                    lead_id=lead.id,
                    activity_type="EMAIL_RECEIVED",
                    description=f"Received reply: {subject}",
                    activity_metadata={"message_id": message_record.id, "sender": sender_email},
                )
                self.db.add(activity)

                # Check if lead is in an active campaign and mark as REPLIED
                cl_stmt = select(CampaignLead).where(
                    CampaignLead.lead_id == lead.id,
                    CampaignLead.status.in_(["PENDING", "IN_PROGRESS"]),
                )
                cl_res = await self.db.execute(cl_stmt)
                cl = cl_res.scalars().first()
                if cl:
                    cl.status = "REPLIED"

                # Update lead pipeline status if NEW/CONTACTED -> INTERESTED
                if lead.pipeline_status in ["NEW", "CONTACTED"]:
                    lead.pipeline_status = "INTERESTED"

                await self.db.commit()

            ingested_count += 1

        return ingested_count
