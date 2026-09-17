from typing import Any
from app.integrations.email.base import EmailMessage, EmailProvider, SendResult


class SMTPProvider(EmailProvider):
    """Placeholder for future production SMTP server integration."""

    async def send(self, message: EmailMessage) -> SendResult:
        raise NotImplementedError("SMTPProvider send is not implemented for production SMTP yet.")

    async def fetch_new_messages(self) -> list[dict[str, Any]]:
        raise NotImplementedError("SMTPProvider fetch_new_messages is not implemented yet.")
