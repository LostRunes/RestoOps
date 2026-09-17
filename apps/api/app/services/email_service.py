from app.integrations.email.base import EmailMessage, EmailProvider, SendResult
from app.integrations.email.mailpit import MailpitProvider
from app.models.campaign import Campaign
from app.models.campaign_step import CampaignStep
from app.models.lead import Lead
from app.services.template_engine import TemplateEngine


class EmailService:
    def __init__(self, provider: EmailProvider | None = None, template_engine: TemplateEngine | None = None):
        self.provider = provider or MailpitProvider()
        self.template_engine = template_engine or TemplateEngine()

    async def send_email(
        self,
        to: str,
        subject: str,
        body_html: str,
        from_addr: str | None = None,
        body_text: str | None = None,
        reply_to: str | None = None,
        message_id: str | None = None,
        in_reply_to: str | None = None,
        references: str | None = None,
        headers: dict | None = None,
    ) -> SendResult:
        msg = EmailMessage(
            to=to,
            from_addr=from_addr or "",
            subject=subject,
            body_html=body_html,
            body_text=body_text,
            reply_to=reply_to,
            message_id=message_id,
            in_reply_to=in_reply_to,
            references=references,
            headers=headers or {},
        )
        return await self.provider.send(msg)

    async def send_campaign_email(
        self,
        lead: Lead,
        step: CampaignStep,
        campaign: Campaign,
        from_addr: str | None = None,
        sender_name: str | None = None,
    ) -> SendResult:
        context = {
            "contact_name": lead.contact_name or "Friend",
            "company_name": lead.company_name or "",
            "restaurant_name": lead.company_name or "Restaurant",
            "sender_name": sender_name or "RestoOps Team",
        }
        subject = self.template_engine.render(step.subject, context)
        body = self.template_engine.render(step.body, context)

        return await self.send_email(
            to=lead.email or "",
            subject=subject,
            body_html=f"<div>{body}</div>",
            body_text=body,
            from_addr=from_addr,
        )
