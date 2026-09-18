"""
AI Service — orchestrates the human-in-the-loop AI workflow.

Flow:
    analyze_conversation() → ConversationAgent → AIRun stored → AIActions created (PROPOSED)
    approve_action()       → Tool executed → AIAction updated to EXECUTED + audit log
    reject_action()        → AIAction updated to REJECTED + audit log
    edit_and_approve()     → Arguments updated → Tool executed → EXECUTED + audit log
"""
from __future__ import annotations
from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.agents.conversation_agent import ConversationAgent
from app.agents.tools import ToolRegistry
from app.core.events import Event, EventBus, EventType
from app.integrations.ollama.client import OllamaClient
from app.models.ai_run import AIRun
from app.models.ai_action import AIAction
from app.models.conversation import Conversation
from app.models.lead import Lead
from app.models.message import Message
from app.repositories.ai_run_repo import AIRunRepository
from app.repositories.ai_action_repo import AIActionRepository
from app.services.audit_service import AuditService
from app.core.config import settings
from app.core.logging import logger


class AIService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.ollama = OllamaClient()
        self.ai_run_repo = AIRunRepository(db)
        self.ai_action_repo = AIActionRepository(db)
        self.audit = AuditService(db)

    async def analyze_conversation(
        self, conversation_id: str, org_id: str
    ) -> dict:
        """
        Fetch conversation + messages + lead, run ConversationAgent,
        store AIRun + AIActions, return analysis dict.
        """
        # Fetch conversation
        result = await self.db.execute(
            select(Conversation).where(
                Conversation.id == conversation_id,
                Conversation.organization_id == org_id,
            )
        )
        conversation = result.scalar_one_or_none()
        if not conversation:
            raise ValueError(f"Conversation {conversation_id} not found")

        # Fetch lead
        lead_result = await self.db.execute(
            select(Lead).where(Lead.id == conversation.lead_id)
        )
        lead = lead_result.scalar_one_or_none()

        # Fetch messages ordered by created_at
        msg_result = await self.db.execute(
            select(Message)
            .where(Message.conversation_id == conversation_id)
            .order_by(Message.created_at)
        )
        messages = list(msg_result.scalars().all())

        # Build context for agent
        context = {
            "lead_id": lead.id if lead else None,
            "lead_email": lead.email if lead else "",
            "lead_company": lead.company_name if lead else "Unknown",
            "lead_contact": lead.contact_name if lead else "Unknown",
            "lead_industry": lead.industry if lead else "Unknown",
            "lead_score": lead.score if lead else 0,
            "lead_priority": lead.priority if lead else "MEDIUM",
            "channel": conversation.channel,
            "messages": [
                {
                    "direction": msg.direction,
                    "date": msg.created_at.strftime("%Y-%m-%d %H:%M") if msg.created_at else "",
                    "body": msg.body,
                }
                for msg in messages
            ],
        }

        # Run conversation agent
        agent = ConversationAgent(self.ollama)
        agent_result = await agent.analyze(context)

        # Store AI run record — log both models used
        model_label = f"{settings.OLLAMA_ANALYSIS_MODEL}+{settings.OLLAMA_TOOL_MODEL}"
        ai_run = await self.ai_run_repo.create(
            org_id=org_id,
            agent=agent_result.agent_name,
            model=model_label,
            input_text=agent.build_prompt(context),
            output_text=agent_result.raw_output,
            structured_output=agent_result.structured_output,
            latency_ms=agent_result.latency_ms,
            tokens=agent_result.tokens_used,
            status=agent_result.status,
            error=agent_result.error,
            conversation_id=conversation_id,
            lead_id=lead.id if lead else None,
        )

        # Create PROPOSED actions for each suggestion
        proposed_actions = []
        if agent_result.analysis and agent_result.status == "COMPLETED":
            for action in agent_result.analysis.suggested_actions:
                db_action = await self.ai_action_repo.create(
                    ai_run_id=ai_run.id,
                    org_id=org_id,
                    tool=action.tool,
                    arguments={
                        **action.arguments,
                        "lead_id": lead.id if lead else None,
                        "_description": action.description,
                        "_confidence": action.confidence,
                    },
                    status="PROPOSED",
                )
                proposed_actions.append(db_action)

        await self.db.commit()

        logger.info(
            "ai_conversation_analyzed",
            conversation_id=conversation_id,
            org_id=org_id,
            status=agent_result.status,
            actions_proposed=len(proposed_actions),
            latency_ms=agent_result.latency_ms,
        )

        return {
            "ai_run_id": ai_run.id,
            "status": agent_result.status,
            "analysis": agent_result.structured_output,
            "actions_proposed": len(proposed_actions),
        }

    async def approve_action(
        self, action_id: str, user_id: str, org_id: str
    ) -> dict:
        """Fetch PROPOSED action, execute tool, mark EXECUTED, audit log."""
        action = await self.ai_action_repo.get_by_id(action_id, org_id)
        if not action:
            raise ValueError(f"Action {action_id} not found")
        if action.status != "PROPOSED":
            raise ValueError(f"Action is not in PROPOSED state (current: {action.status})")

        # Execute the tool
        args = {k: v for k, v in action.arguments.items() if not k.startswith("_")}
        try:
            exec_result = await ToolRegistry.execute(action.tool, **args)
            new_status = "EXECUTED"
        except Exception as exc:
            exec_result = {"error": str(exc)}
            new_status = "FAILED"

        now = datetime.now(timezone.utc)
        await self.ai_action_repo.update(
            action_id,
            status=new_status,
            approved_by=user_id,
            approved_at=now,
            executed_at=now,
            result=exec_result,
        )

        await self.audit.log(
            org_id=org_id,
            user_id=user_id,
            action="AI_ACTION_APPROVED",
            entity_type="ai_action",
            entity_id=action_id,
            old_value={"status": "PROPOSED"},
            new_value={"status": new_status, "tool": action.tool},
        )

        await self.db.commit()
        await EventBus.publish(Event(
            EventType.AI_ACTION_APPROVED, org_id,
            {"action_id": action_id, "tool_name": action.tool, "status": new_status},
            user_id=user_id,
        ))
        return {"status": new_status, "result": exec_result}

    async def reject_action(
        self, action_id: str, user_id: str, org_id: str, reason: str
    ) -> None:
        """Mark action as REJECTED with reason."""
        action = await self.ai_action_repo.get_by_id(action_id, org_id)
        if not action:
            raise ValueError(f"Action {action_id} not found")
        if action.status != "PROPOSED":
            raise ValueError(f"Action is not in PROPOSED state (current: {action.status})")

        await self.ai_action_repo.update(
            action_id,
            status="REJECTED",
            rejection_reason=reason,
        )

        await self.audit.log(
            org_id=org_id,
            user_id=user_id,
            action="AI_ACTION_REJECTED",
            entity_type="ai_action",
            entity_id=action_id,
            old_value={"status": "PROPOSED"},
            new_value={"status": "REJECTED", "reason": reason},
        )

        await self.db.commit()

    async def edit_and_approve(
        self, action_id: str, user_id: str, org_id: str, new_arguments: dict
    ) -> dict:
        """Update action arguments and then execute."""
        action = await self.ai_action_repo.get_by_id(action_id, org_id)
        if not action:
            raise ValueError(f"Action {action_id} not found")
        if action.status != "PROPOSED":
            raise ValueError(f"Action is not in PROPOSED state (current: {action.status})")

        # Merge new arguments with existing (strip internal _keys)
        merged = {k: v for k, v in action.arguments.items() if k.startswith("_")}
        merged.update(new_arguments)
        await self.ai_action_repo.update(action_id, arguments=merged)

        # Now approve with updated arguments
        return await self.approve_action(action_id, user_id, org_id)

    async def list_pending_actions(self, org_id: str) -> list[AIAction]:
        """List all PROPOSED actions for the org."""
        return await self.ai_action_repo.list_pending(org_id)

    async def get_ai_activity(
        self, org_id: str, page: int = 1
    ) -> list[AIRun]:
        """Paginated list of all AI runs."""
        return await self.ai_run_repo.list_by_org(org_id, page=page)
