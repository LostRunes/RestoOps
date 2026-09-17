import asyncio
import email.mime.multipart
import email.mime.text
import smtplib
import uuid
import httpx
from typing import Any

from app.core.config import settings
from app.integrations.email.base import EmailMessage, EmailProvider, SendResult


class MailpitProvider(EmailProvider):
    def __init__(
        self,
        smtp_host: str = settings.SMTP_HOST,
        smtp_port: int = settings.SMTP_PORT,
        mailpit_http_url: str = settings.MAILPIT_HTTP_URL,
        from_addr: str = settings.EMAILS_FROM_EMAIL,
    ):
        self.smtp_host = smtp_host
        self.smtp_port = smtp_port
        self.mailpit_http_url = mailpit_http_url
        self.default_from_addr = from_addr

    def _build_mime_msg(self, message: EmailMessage) -> tuple[email.mime.multipart.MIMEMultipart, str]:
        msg = email.mime.multipart.MIMEMultipart("alternative")
        msg["From"] = message.from_addr or self.default_from_addr
        msg["To"] = message.to
        msg["Subject"] = message.subject or ""

        msg_id = message.message_id or f"<{uuid.uuid4()}@restoops.local>"
        msg["Message-ID"] = msg_id

        if message.reply_to:
            msg["Reply-To"] = message.reply_to
        if message.in_reply_to:
            msg["In-Reply-To"] = message.in_reply_to
        if message.references:
            msg["References"] = message.references

        if message.headers:
            for k, v in message.headers.items():
                msg[k] = str(v)

        if message.body_text:
            msg.attach(email.mime.text.MIMEText(message.body_text, "plain", "utf-8"))
        if message.body_html:
            msg.attach(email.mime.text.MIMEText(message.body_html, "html", "utf-8"))

        return msg, msg_id

    def _send_sync(self, message: EmailMessage) -> SendResult:
        try:
            msg, msg_id = self._build_mime_msg(message)
            with smtplib.SMTP(self.smtp_host, self.smtp_port, timeout=10) as client:
                client.send_message(msg)
            return SendResult(success=True, message_id=msg_id)
        except Exception as e:
            return SendResult(success=False, message_id=None, error=str(e))

    async def send(self, message: EmailMessage) -> SendResult:
        return await asyncio.to_thread(self._send_sync, message)

    async def fetch_new_messages(self) -> list[dict[str, Any]]:
        url = f"{self.mailpit_http_url.rstrip('/')}/api/v1/messages"
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                res = await client.get(url)
                if res.status_code == 200:
                    data = res.json()
                    return data.get("messages", [])
                return []
        except Exception:
            return []
