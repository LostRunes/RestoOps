from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.conversation import Conversation
from app.models.lead import Lead
from app.repositories.conversation_repo import ConversationRepository
from app.repositories.message_repo import MessageRepository


class ConversationMatcher:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.conv_repo = ConversationRepository(db)
        self.msg_repo = MessageRepository(db)

    async def match(
        self,
        message_headers: dict[str, str],
        org_id: str,
        sender_email: str,
        subject: str | None = None,
    ) -> Conversation:
        in_reply_to = message_headers.get("In-Reply-To") or message_headers.get("in-reply-to")
        if in_reply_to:
            matched_msg = await self.msg_repo.get_by_message_id(in_reply_to.strip())
            if matched_msg:
                conv = await self.conv_repo.get_by_id(matched_msg.conversation_id, org_id)
                if conv:
                    return conv

        references_str = message_headers.get("References") or message_headers.get("references")
        if references_str:
            refs = [r.strip() for r in references_str.replace("\n", " ").split(" ") if r.strip()]
            matched_msg = await self.msg_repo.find_by_references(refs)
            if matched_msg:
                conv = await self.conv_repo.get_by_id(matched_msg.conversation_id, org_id)
                if conv:
                    return conv

        # Lookup lead by sender_email in the organization
        lead_stmt = select(Lead).where(
            Lead.organization_id == org_id,
            Lead.email == sender_email.strip().lower(),
        )
        result = await self.db.execute(lead_stmt)
        lead = result.scalar_one_or_none()

        if not lead:
            # Create a lead for unknown inbound email
            lead = Lead(
                organization_id=org_id,
                contact_name=sender_email.split("@")[0].title(),
                email=sender_email.strip().lower(),
                source="EMAIL_INBOUND",
                pipeline_status="NEW",
            )
            self.db.add(lead)
            await self.db.commit()
            await self.db.refresh(lead)

        # Check existing conversation for lead
        conv = await self.conv_repo.get_by_lead(lead.id, org_id, channel="EMAIL")
        if conv:
            return conv

        # Create new conversation
        return await self.conv_repo.create(
            org_id=org_id,
            lead_id=lead.id,
            channel="EMAIL",
            subject=subject,
        )
