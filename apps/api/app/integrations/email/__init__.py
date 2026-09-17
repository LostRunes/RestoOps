from app.integrations.email.base import EmailMessage, EmailProvider, SendResult
from app.integrations.email.mailpit import MailpitProvider
from app.integrations.email.smtp_provider import SMTPProvider

__all__ = [
    "EmailMessage",
    "SendResult",
    "EmailProvider",
    "MailpitProvider",
    "SMTPProvider",
]
