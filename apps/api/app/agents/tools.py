"""
Tool registry — defines all tools the AI can suggest calling.
Handlers are registered here and executed after human approval.
"""
from __future__ import annotations
from typing import Callable
from app.core.logging import logger


class ToolRegistry:
    """Registry of tools the AI can suggest calling."""

    _tools: dict[str, dict] = {}

    @classmethod
    def register(
        cls,
        name: str,
        description: str,
        handler: Callable,
        requires_approval: bool = True,
    ):
        cls._tools[name] = {
            "name": name,
            "description": description,
            "handler": handler,
            "requires_approval": requires_approval,
        }

    @classmethod
    def get_tool(cls, name: str) -> dict | None:
        return cls._tools.get(name)

    @classmethod
    def list_tools(cls) -> list[str]:
        return list(cls._tools.keys())

    @classmethod
    async def execute(cls, name: str, **kwargs) -> dict:
        tool = cls._tools.get(name)
        if not tool:
            raise ValueError(f"Unknown tool: '{name}'. Available: {list(cls._tools.keys())}")
        handler = tool["handler"]
        # Support both async and sync handlers
        import asyncio, inspect
        if inspect.iscoroutinefunction(handler):
            return await handler(**kwargs)
        return handler(**kwargs)


# ---------------------------------------------------------------------------
# Tool handler stubs — these will be wired to real services in later phases
# ---------------------------------------------------------------------------

async def _create_quote(lead_id: str, guest_count: int = None, event_date: str = None,
                         event_type: str = None, **kwargs) -> dict:
    """Placeholder — Phase 6 will implement the full quote creation flow."""
    return {
        "status": "draft_created",
        "note": "Quote creation will be fully implemented in Phase 6.",
        "lead_id": lead_id,
        "guest_count": guest_count,
        "event_date": event_date,
        "event_type": event_type,
    }


async def _send_email(lead_id: str, subject: str = "", body: str = "", **kwargs) -> dict:
    """Placeholder — uses Phase 4 email service when wired."""
    return {
        "status": "queued",
        "note": "Email sending will be wired to campaign email service.",
        "lead_id": lead_id,
        "subject": subject,
    }


async def _update_lead(lead_id: str, pipeline_status: str = None, priority: str = None,
                        **kwargs) -> dict:
    """Placeholder — updates lead pipeline status."""
    return {
        "status": "updated",
        "lead_id": lead_id,
        "pipeline_status": pipeline_status,
        "priority": priority,
    }


async def _schedule_followup(lead_id: str, follow_up_date: str = None,
                              note: str = "", **kwargs) -> dict:
    """Placeholder — creates follow-up task."""
    return {
        "status": "scheduled",
        "lead_id": lead_id,
        "follow_up_date": follow_up_date,
        "note": note,
    }


async def _create_task(lead_id: str, title: str = "", description: str = "",
                        assigned_to: str = None, **kwargs) -> dict:
    """Placeholder — creates a manual staff task."""
    return {
        "status": "created",
        "lead_id": lead_id,
        "title": title,
    }


async def _add_suppression(email: str, reason: str = "opt_out", **kwargs) -> dict:
    """Placeholder — adds email to suppression list."""
    return {
        "status": "suppressed",
        "email": email,
        "reason": reason,
    }


# Register all tools
ToolRegistry.register(
    "create_quote",
    "Create a draft catering quote for a lead based on event details",
    _create_quote,
    requires_approval=True,
)
ToolRegistry.register(
    "send_email",
    "Send an email to the lead",
    _send_email,
    requires_approval=True,
)
ToolRegistry.register(
    "update_lead",
    "Update the lead's pipeline status or priority",
    _update_lead,
    requires_approval=True,
)
ToolRegistry.register(
    "schedule_followup",
    "Schedule a follow-up task for a lead",
    _schedule_followup,
    requires_approval=True,
)
ToolRegistry.register(
    "create_task",
    "Create a manual task for staff",
    _create_task,
    requires_approval=True,
)
ToolRegistry.register(
    "add_suppression",
    "Add the lead's email to the suppression list (opt-out)",
    _add_suppression,
    requires_approval=True,
)
