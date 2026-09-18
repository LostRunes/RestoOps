"""
Gmail API Provider for RestoOps.

Uses OAuth2 with offline access (refresh token) to send and read emails
via the Gmail REST API. No SMTP needed — works with any Gmail/Google Workspace
account as long as you've done the one-time consent flow.

Scopes used: gmail.modify (send + read + modify — no permanent delete)

Setup:
  1. Run: python scripts/gmail_oauth_setup.py
  2. Follow the browser prompt, log in, grant access
  3. Copy the printed refresh token into .env as GMAIL_REFRESH_TOKEN
  4. Set GMAIL_SENDER_EMAIL to the Gmail address you authorized

After that, the backend uses the refresh token to get short-lived access
tokens automatically — no user interaction ever needed again.
"""

import asyncio
import base64
import email as email_lib
import email.mime.multipart
import email.mime.text
import uuid
from typing import Any

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from app.core.config import settings
from app.integrations.email.base import EmailMessage, EmailProvider, SendResult


def _build_service():
    """Build and return an authenticated Gmail API service object."""
    creds = Credentials(
        token=None,
        refresh_token=settings.GMAIL_REFRESH_TOKEN,
        token_uri="https://oauth2.googleapis.com/token",
        client_id=settings.GMAIL_CLIENT_ID,
        client_secret=settings.GMAIL_CLIENT_SECRET,
        scopes=["https://www.googleapis.com/auth/gmail.modify"],
    )
    # Refresh to get a valid access token
    creds.refresh(Request())
    return build("gmail", "v1", credentials=creds, cache_discovery=False)


def _build_mime_message(message: EmailMessage) -> tuple[str, str]:
    """Build a MIME message and return (raw_base64url, message_id)."""
    mime = email_lib.mime.multipart.MIMEMultipart("alternative")
    from_addr = message.from_addr or settings.GMAIL_SENDER_EMAIL
    mime["From"] = from_addr
    mime["To"] = message.to
    mime["Subject"] = message.subject or ""

    msg_id = message.message_id or f"<{uuid.uuid4()}@restoops.gmail>"
    mime["Message-ID"] = msg_id

    if message.reply_to:
        mime["Reply-To"] = message.reply_to
    if message.in_reply_to:
        mime["In-Reply-To"] = message.in_reply_to
    if message.references:
        mime["References"] = message.references

    if message.headers:
        for k, v in message.headers.items():
            mime[k] = str(v)

    if message.body_text:
        mime.attach(email_lib.mime.text.MIMEText(message.body_text, "plain", "utf-8"))
    if message.body_html:
        mime.attach(email_lib.mime.text.MIMEText(message.body_html, "html", "utf-8"))

    raw = base64.urlsafe_b64encode(mime.as_bytes()).decode("utf-8")
    return raw, msg_id


def _send_sync(message: EmailMessage) -> SendResult:
    """Synchronous send via Gmail API (run in thread pool)."""
    if not settings.GMAIL_REFRESH_TOKEN:
        return SendResult(
            success=False,
            message_id=None,
            error="GMAIL_REFRESH_TOKEN not set. Run scripts/gmail_oauth_setup.py first.",
        )
    try:
        service = _build_service()
        raw, msg_id = _build_mime_message(message)
        service.users().messages().send(
            userId="me",
            body={"raw": raw},
        ).execute()
        return SendResult(success=True, message_id=msg_id)
    except HttpError as e:
        return SendResult(success=False, message_id=None, error=f"Gmail API error: {e}")
    except Exception as e:
        return SendResult(success=False, message_id=None, error=str(e))


def _fetch_sync(max_results: int = 20) -> list[dict[str, Any]]:
    """
    Synchronous fetch of unread messages from inbox (run in thread pool).
    Returns a list of parsed message dicts suitable for inbound processing.
    """
    if not settings.GMAIL_REFRESH_TOKEN:
        return []
    try:
        service = _build_service()
        # List unread messages in INBOX
        result = service.users().messages().list(
            userId="me",
            labelIds=["INBOX", "UNREAD"],
            maxResults=max_results,
        ).execute()

        messages_raw = result.get("messages", [])
        parsed = []
        for m in messages_raw:
            msg = service.users().messages().get(
                userId="me",
                id=m["id"],
                format="full",
            ).execute()

            headers = {
                h["name"].lower(): h["value"]
                for h in msg.get("payload", {}).get("headers", [])
            }

            # Extract text body
            body_text = ""
            body_html = ""
            payload = msg.get("payload", {})

            def _extract_body(parts):
                nonlocal body_text, body_html
                for part in parts:
                    mime_type = part.get("mimeType", "")
                    data = part.get("body", {}).get("data", "")
                    if data:
                        decoded = base64.urlsafe_b64decode(data + "==").decode("utf-8", errors="replace")
                        if mime_type == "text/plain":
                            body_text = decoded
                        elif mime_type == "text/html":
                            body_html = decoded
                    if part.get("parts"):
                        _extract_body(part["parts"])

            if payload.get("parts"):
                _extract_body(payload["parts"])
            elif payload.get("body", {}).get("data"):
                data = payload["body"]["data"]
                decoded = base64.urlsafe_b64decode(data + "==").decode("utf-8", errors="replace")
                if payload.get("mimeType") == "text/html":
                    body_html = decoded
                else:
                    body_text = decoded

            parsed.append({
                "id": msg["id"],
                "thread_id": msg.get("threadId"),
                "from": headers.get("from", ""),
                "to": headers.get("to", ""),
                "subject": headers.get("subject", ""),
                "message_id": headers.get("message-id", ""),
                "in_reply_to": headers.get("in-reply-to", ""),
                "references": headers.get("references", ""),
                "date": headers.get("date", ""),
                "body_text": body_text,
                "body_html": body_html,
                "label_ids": msg.get("labelIds", []),
            })

            # Mark as read
            service.users().messages().modify(
                userId="me",
                id=m["id"],
                body={"removeLabelIds": ["UNREAD"]},
            ).execute()

        return parsed
    except Exception:
        return []


class GmailProvider(EmailProvider):
    """
    Gmail API email provider.

    Sending: Uses Gmail API to send real emails via your Gmail account.
    Receiving: Fetches unread INBOX messages and marks them as read.

    Requires GMAIL_CLIENT_ID, GMAIL_CLIENT_SECRET, GMAIL_REFRESH_TOKEN,
    and GMAIL_SENDER_EMAIL in your .env.
    """

    async def send(self, message: EmailMessage) -> SendResult:
        return await asyncio.to_thread(_send_sync, message)

    async def fetch_new_messages(self) -> list[dict[str, Any]]:
        return await asyncio.to_thread(_fetch_sync)
