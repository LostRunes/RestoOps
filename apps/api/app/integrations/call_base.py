from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from uuid import UUID


@dataclass
class CallRequest:
    """Data required to initiate a call via any provider."""
    lead_id: UUID
    from_identifier: str    # Agent's phone number (Exotel) or user_id (WebRTC)
    to_identifier: str      # Lead's phone number (Exotel) or peer user_id (WebRTC)
    org_id: UUID
    initiated_by: UUID
    metadata: dict = field(default_factory=dict)


@dataclass
class CallResult:
    """Result returned by a call provider after initiating a call."""
    success: bool
    # Provider-specific call identifier: Exotel Sid or WebRTC room_id
    call_id: str | None
    status: str
    error: str | None = None
    extra: dict = field(default_factory=dict)


class CallProvider(ABC):
    """Abstract base class for all call providers."""

    @abstractmethod
    async def initiate_call(self, request: CallRequest) -> CallResult:
        """Start a call. Returns a CallResult with provider call ID."""

    @abstractmethod
    async def end_call(self, provider_call_id: str) -> bool:
        """End or cancel an active call. Returns True if successful."""

    @abstractmethod
    async def get_call_status(self, provider_call_id: str) -> str:
        """Fetch the current call status from the provider. Returns our status string."""
