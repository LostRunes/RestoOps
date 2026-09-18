"""
Internal event bus for RestoOps.

Provides a simple in-process pub/sub mechanism:
- Publishers call EventBus.publish(event) after any significant state change.
- Subscribers (notification handlers, analytics, etc.) register via EventBus.subscribe().
- Errors in individual handlers are logged but never bubble up to the caller.

This is intentionally kept in-process and lightweight. If multi-process fan-out
is ever needed, swap the inner loop for Redis pub/sub without changing call sites.
"""
from __future__ import annotations

import asyncio
from enum import Enum
from typing import Callable, Any

import structlog

logger = structlog.get_logger()


class EventType(str, Enum):
    # Leads
    LEAD_CREATED = "LEAD_CREATED"
    LEAD_UPDATED = "LEAD_UPDATED"
    LEAD_VERIFIED = "LEAD_VERIFIED"
    LEAD_REPLIED = "LEAD_REPLIED"
    LEAD_IMPORTED = "LEAD_IMPORTED"

    # Campaigns
    CAMPAIGN_STARTED = "CAMPAIGN_STARTED"
    CAMPAIGN_COMPLETED = "CAMPAIGN_COMPLETED"
    CAMPAIGN_PAUSED = "CAMPAIGN_PAUSED"

    # Quotes
    QUOTE_CREATED = "QUOTE_CREATED"
    QUOTE_SENT = "QUOTE_SENT"
    QUOTE_VIEWED = "QUOTE_VIEWED"
    QUOTE_ACCEPTED = "QUOTE_ACCEPTED"
    QUOTE_REJECTED = "QUOTE_REJECTED"
    QUOTE_EXPIRED = "QUOTE_EXPIRED"

    # Orders
    ORDER_CREATED = "ORDER_CREATED"
    ORDER_COMPLETED = "ORDER_COMPLETED"

    # Calls
    CALL_STARTED = "CALL_STARTED"
    CALL_ANSWERED = "CALL_ANSWERED"
    CALL_ENDED = "CALL_ENDED"

    # AI
    AI_ACTION_PROPOSED = "AI_ACTION_PROPOSED"
    AI_ACTION_APPROVED = "AI_ACTION_APPROVED"
    AI_ACTION_REJECTED = "AI_ACTION_REJECTED"

    # Jobs / Verification
    VERIFICATION_COMPLETED = "VERIFICATION_COMPLETED"
    JOB_COMPLETED = "JOB_COMPLETED"
    JOB_FAILED = "JOB_FAILED"

    # Follow-ups
    FOLLOWUP_DUE = "FOLLOWUP_DUE"


class Event:
    """
    Carries event context from publisher to all subscribed handlers.

    Attributes:
        type:    The EventType that occurred.
        org_id:  The organization this event belongs to.
        data:    Event-specific payload dict (entity IDs, names, amounts, etc.)
        user_id: The user who triggered the event (optional — some events are system-generated).
    """

    def __init__(
        self,
        type: EventType,
        org_id: str,
        data: dict[str, Any],
        user_id: str | None = None,
    ):
        self.type = type
        self.org_id = org_id
        self.user_id = user_id
        self.data = data

    def __repr__(self) -> str:
        return f"<Event type={self.type} org={self.org_id} user={self.user_id}>"


class EventBus:
    """
    Simple singleton in-process event bus.

    Usage:
        # Register a handler (at startup):
        EventBus.subscribe(EventType.QUOTE_ACCEPTED, my_handler)

        # Publish an event (anywhere in a service):
        await EventBus.publish(Event(EventType.QUOTE_ACCEPTED, org_id, {...}))
    """

    _handlers: dict[EventType, list[Callable]] = {}

    @classmethod
    def subscribe(cls, event_type: EventType, handler: Callable) -> None:
        """Register an async handler for an event type. May be called multiple times."""
        if event_type not in cls._handlers:
            cls._handlers[event_type] = []
        cls._handlers[event_type].append(handler)

    @classmethod
    def reset(cls) -> None:
        """Clear all handlers. Used in tests to avoid cross-test pollution."""
        cls._handlers = {}

    @classmethod
    async def publish(cls, event: Event) -> None:
        """
        Publish an event. All registered handlers are called concurrently.
        Individual handler failures are caught and logged — they never block the caller.
        """
        handlers = cls._handlers.get(event.type, [])
        if not handlers:
            return

        async def _run(handler: Callable) -> None:
            try:
                await handler(event)
            except Exception as exc:
                logger.error(
                    "Event handler failed",
                    event_type=event.type,
                    handler=getattr(handler, "__name__", repr(handler)),
                    error=str(exc),
                )

        await asyncio.gather(*[_run(h) for h in handlers], return_exceptions=False)
