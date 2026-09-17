from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any


@dataclass
class EmailMessage:
    to: str
    from_addr: str
    subject: str
    body_html: str
    body_text: str | None = None
    reply_to: str | None = None
    message_id: str | None = None  # Custom Message-ID
    in_reply_to: str | None = None
    references: str | None = None
    headers: dict[str, str] = field(default_factory=dict)


@dataclass
class SendResult:
    success: bool
    message_id: str | None = None
    error: str | None = None


class EmailProvider(ABC):
    @abstractmethod
    async def send(self, message: EmailMessage) -> SendResult:
        """Send an email. Returns SendResult."""
        pass

    @abstractmethod
    async def fetch_new_messages(self) -> list[dict[str, Any]]:
        """Fetch unread messages from inbox. Returns raw message dicts."""
        pass
