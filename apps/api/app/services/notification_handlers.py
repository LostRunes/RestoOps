"""
Notification event handlers.

Each handler is subscribed to a specific EventType via EventBus.subscribe()
and creates the appropriate notifications when that event fires.

All handlers follow the same pattern:
  1. Extract relevant data from event.data
  2. Build a human-readable title + body
  3. Call notification_service.create_for_org_roles() or create_notification()
  4. Return (errors are caught by the EventBus and logged)

Because handlers need a DB session and notification_service instance,
they create their own sessions via AsyncSessionLocal. This is safe because
events are published after the emitting transaction has committed.
"""
from __future__ import annotations

from app.core.events import Event, EventBus, EventType
from app.core.logging import logger
from app.db.session import AsyncSessionLocal
from app.services.notification_service import NotificationService


# ---------------------------------------------------------------------------
# Individual handlers
# ---------------------------------------------------------------------------

async def on_lead_created(event: Event) -> None:
    data = event.data
    async with AsyncSessionLocal() as db:
        svc = NotificationService(db)
        await svc.create_for_org_admins(
            org_id=event.org_id,
            type="LEAD_CREATED",
            title=f"New lead: {data.get('company_name', 'Unknown')}",
            body=f"A new lead has been added: {data.get('contact_name', '')} from {data.get('company_name', '')}.",
            entity_type="lead",
            entity_id=data.get("lead_id"),
            priority="NORMAL",
        )


async def on_lead_replied(event: Event) -> None:
    data = event.data
    async with AsyncSessionLocal() as db:
        svc = NotificationService(db)
        await svc.create_for_org_roles(
            org_id=event.org_id,
            role_names=["OWNER", "ADMIN", "MANAGER", "AGENT"],
            type="LEAD_REPLIED",
            title=f"New reply from {data.get('contact_name', 'a lead')}",
            body=f"{data.get('company_name', 'A lead')} replied to your email.",
            entity_type="lead",
            entity_id=data.get("lead_id"),
            priority="HIGH",
            metadata={"conversation_id": data.get("conversation_id")},
        )


async def on_lead_verified(event: Event) -> None:
    data = event.data
    if not event.user_id:
        return
    async with AsyncSessionLocal() as db:
        svc = NotificationService(db)
        await svc.create_notification(
            org_id=event.org_id,
            user_id=event.user_id,
            type="LEAD_VERIFIED",
            title="Lead verification completed",
            body=f"Email verification completed with status: {data.get('status', 'UNKNOWN')}.",
            entity_type="lead",
            entity_id=data.get("lead_id"),
            priority="NORMAL",
        )


async def on_verification_completed(event: Event) -> None:
    data = event.data
    if not event.user_id:
        return
    results = data.get("results", {})
    total = results.get("total", 0)
    valid = results.get("valid", 0)
    invalid = results.get("invalid", 0)
    async with AsyncSessionLocal() as db:
        svc = NotificationService(db)
        await svc.create_notification(
            org_id=event.org_id,
            user_id=event.user_id,
            type="VERIFICATION_COMPLETED",
            title="Verification job completed",
            body=f"{valid} valid, {invalid} invalid out of {total} leads.",
            entity_type="job",
            entity_id=data.get("job_id"),
            priority="NORMAL",
            metadata=results,
        )


async def on_quote_sent(event: Event) -> None:
    data = event.data
    async with AsyncSessionLocal() as db:
        svc = NotificationService(db)
        await svc.create_for_org_admins(
            org_id=event.org_id,
            type="QUOTE_SENT",
            title=f"Quote #{data.get('quote_number', '')} sent",
            body=f"Quote sent to {data.get('lead_email', 'the lead')} for ${data.get('total', 0):.2f}.",
            entity_type="quote",
            entity_id=data.get("quote_id"),
            priority="NORMAL",
        )


async def on_quote_accepted(event: Event) -> None:
    data = event.data
    async with AsyncSessionLocal() as db:
        svc = NotificationService(db)
        await svc.create_for_org_admins(
            org_id=event.org_id,
            type="QUOTE_ACCEPTED",
            title=f"🎉 Quote #{data.get('quote_number', '')} accepted!",
            body=f"{data.get('company_name', 'A lead')} accepted the quote for ${data.get('total', 0):.2f}.",
            entity_type="quote",
            entity_id=data.get("quote_id"),
            priority="URGENT",
            metadata={"order_id": data.get("order_id")},
        )


async def on_quote_rejected(event: Event) -> None:
    data = event.data
    async with AsyncSessionLocal() as db:
        svc = NotificationService(db)
        await svc.create_for_org_admins(
            org_id=event.org_id,
            type="QUOTE_REJECTED",
            title=f"Quote #{data.get('quote_number', '')} rejected",
            body=f"{data.get('company_name', 'A lead')} rejected the quote.",
            entity_type="quote",
            entity_id=data.get("quote_id"),
            priority="HIGH",
        )


async def on_quote_expired(event: Event) -> None:
    data = event.data
    async with AsyncSessionLocal() as db:
        svc = NotificationService(db)
        await svc.create_for_org_admins(
            org_id=event.org_id,
            type="QUOTE_EXPIRED",
            title=f"Quote #{data.get('quote_number', '')} expired",
            body=f"Quote for {data.get('company_name', 'a lead')} has expired without a response.",
            entity_type="quote",
            entity_id=data.get("quote_id"),
            priority="NORMAL",
        )


async def on_order_created(event: Event) -> None:
    data = event.data
    async with AsyncSessionLocal() as db:
        svc = NotificationService(db)
        await svc.create_for_org_admins(
            org_id=event.org_id,
            type="ORDER_CREATED",
            title=f"New order: #{data.get('order_number', '')}",
            body=f"Order created for ${data.get('total', 0):.2f} from {data.get('company_name', 'a lead')}.",
            entity_type="order",
            entity_id=data.get("order_id"),
            priority="HIGH",
        )


async def on_ai_action_proposed(event: Event) -> None:
    data = event.data
    async with AsyncSessionLocal() as db:
        svc = NotificationService(db)
        await svc.create_for_org_roles(
            org_id=event.org_id,
            role_names=["OWNER", "ADMIN", "MANAGER"],
            type="AI_ACTION_PROPOSED",
            title=f"AI suggested: {data.get('tool_name', 'an action')}",
            body=f"Review and approve the AI's recommendation: {data.get('description', '')}",
            entity_type="ai_action",
            entity_id=data.get("action_id"),
            priority="HIGH",
        )


async def on_ai_action_approved(event: Event) -> None:
    data = event.data
    if not event.user_id:
        return
    async with AsyncSessionLocal() as db:
        svc = NotificationService(db)
        await svc.create_notification(
            org_id=event.org_id,
            user_id=event.user_id,
            type="AI_ACTION_APPROVED",
            title="AI action approved and executed",
            body=f"Action '{data.get('tool_name', '')}' was approved and has been executed.",
            entity_type="ai_action",
            entity_id=data.get("action_id"),
            priority="NORMAL",
        )


async def on_call_ended(event: Event) -> None:
    data = event.data
    if not event.user_id:
        return
    duration = data.get("duration_seconds")
    duration_str = f", duration {duration}s" if duration else ""
    async with AsyncSessionLocal() as db:
        svc = NotificationService(db)
        await svc.create_notification(
            org_id=event.org_id,
            user_id=event.user_id,
            type="CALL_COMPLETED",
            title=f"Call completed with {data.get('contact_name', 'lead')}",
            body=f"Call ended with status {data.get('status', 'COMPLETED')}{duration_str}.",
            entity_type="call",
            entity_id=data.get("call_id"),
            priority="NORMAL",
        )


async def on_campaign_started(event: Event) -> None:
    data = event.data
    async with AsyncSessionLocal() as db:
        svc = NotificationService(db)
        await svc.create_for_org_admins(
            org_id=event.org_id,
            type="CAMPAIGN_STARTED",
            title=f"Campaign '{data.get('campaign_name', '')}' started",
            body=f"Campaign is now active with {data.get('lead_count', 0)} leads enrolled.",
            entity_type="campaign",
            entity_id=data.get("campaign_id"),
            priority="NORMAL",
        )


async def on_campaign_completed(event: Event) -> None:
    data = event.data
    async with AsyncSessionLocal() as db:
        svc = NotificationService(db)
        await svc.create_for_org_admins(
            org_id=event.org_id,
            type="CAMPAIGN_COMPLETED",
            title=f"Campaign '{data.get('campaign_name', '')}' completed",
            body=f"{data.get('total', 0)} leads contacted, {data.get('replied', 0)} replies received.",
            entity_type="campaign",
            entity_id=data.get("campaign_id"),
            priority="NORMAL",
        )


async def on_followup_due(event: Event) -> None:
    data = event.data
    if not event.user_id:
        return
    async with AsyncSessionLocal() as db:
        svc = NotificationService(db)
        await svc.create_notification(
            org_id=event.org_id,
            user_id=event.user_id,
            type="FOLLOWUP_DUE",
            title=f"Follow-up due: {data.get('company_name', 'a lead')}",
            body=f"Scheduled follow-up for {data.get('contact_name', 'the lead')} is due now.",
            entity_type="lead",
            entity_id=data.get("lead_id"),
            priority="HIGH",
        )


# ---------------------------------------------------------------------------
# Registration
# ---------------------------------------------------------------------------

def register_notification_handlers() -> None:
    """
    Register all notification handlers with the EventBus.
    Call this once at application startup (in FastAPI lifespan).
    """
    EventBus.subscribe(EventType.LEAD_CREATED, on_lead_created)
    EventBus.subscribe(EventType.LEAD_REPLIED, on_lead_replied)
    EventBus.subscribe(EventType.LEAD_VERIFIED, on_lead_verified)
    EventBus.subscribe(EventType.VERIFICATION_COMPLETED, on_verification_completed)
    EventBus.subscribe(EventType.QUOTE_SENT, on_quote_sent)
    EventBus.subscribe(EventType.QUOTE_ACCEPTED, on_quote_accepted)
    EventBus.subscribe(EventType.QUOTE_REJECTED, on_quote_rejected)
    EventBus.subscribe(EventType.QUOTE_EXPIRED, on_quote_expired)
    EventBus.subscribe(EventType.ORDER_CREATED, on_order_created)
    EventBus.subscribe(EventType.AI_ACTION_PROPOSED, on_ai_action_proposed)
    EventBus.subscribe(EventType.AI_ACTION_APPROVED, on_ai_action_approved)
    EventBus.subscribe(EventType.CALL_ENDED, on_call_ended)
    EventBus.subscribe(EventType.CAMPAIGN_STARTED, on_campaign_started)
    EventBus.subscribe(EventType.CAMPAIGN_COMPLETED, on_campaign_completed)
    EventBus.subscribe(EventType.FOLLOWUP_DUE, on_followup_due)

    logger.info("NotificationHandlers: all handlers registered", count=15)
