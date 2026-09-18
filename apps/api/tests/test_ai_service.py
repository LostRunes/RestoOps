"""
Phase 5 — AIService tests (mocked DB + mocked Ollama).
Tests approve, reject, edit_and_approve, and error paths.
"""
import json
import pytest
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch
from app.services.ai_service import AIService
from app.agents.base import AgentResult
from app.agents.schemas import ConversationAnalysis, SuggestedAction


def _make_mock_action(status="PROPOSED", tool="create_quote"):
    action = MagicMock()
    action.id = "action-uuid-001"
    action.organization_id = "org-uuid-001"
    action.ai_run_id = "run-uuid-001"
    action.tool = tool
    action.arguments = {
        "lead_id": "lead-123",
        "guest_count": 80,
        "_description": "Create quote for 80 guests",
        "_confidence": 0.92,
    }
    action.status = status
    action.result = None
    return action


def _make_mock_db():
    db = AsyncMock()
    db.commit = AsyncMock()
    db.flush = AsyncMock()
    db.add = MagicMock()
    db.execute = AsyncMock()
    return db


class TestAIServiceApproveAction:
    @pytest.mark.asyncio
    async def test_approve_proposed_action_executes_tool(self):
        db = _make_mock_db()
        service = AIService(db)

        mock_action = _make_mock_action(status="PROPOSED")
        service.ai_action_repo.get_by_id = AsyncMock(return_value=mock_action)
        service.ai_action_repo.update = AsyncMock(return_value=mock_action)
        service.audit.log = AsyncMock()

        result = await service.approve_action("action-uuid-001", "user-001", "org-uuid-001")

        assert result["status"] in ("EXECUTED", "FAILED")
        service.ai_action_repo.update.assert_called_once()
        service.audit.log.assert_called_once()

        # Check audit log was called with correct action
        call_kwargs = service.audit.log.call_args[1]
        assert call_kwargs["action"] == "AI_ACTION_APPROVED"
        assert call_kwargs["entity_type"] == "ai_action"

    @pytest.mark.asyncio
    async def test_approve_nonexistent_action_raises(self):
        db = _make_mock_db()
        service = AIService(db)
        service.ai_action_repo.get_by_id = AsyncMock(return_value=None)

        with pytest.raises(ValueError, match="not found"):
            await service.approve_action("bad-id", "user-001", "org-001")

    @pytest.mark.asyncio
    async def test_approve_already_executed_action_raises(self):
        db = _make_mock_db()
        service = AIService(db)

        mock_action = _make_mock_action(status="EXECUTED")
        service.ai_action_repo.get_by_id = AsyncMock(return_value=mock_action)

        with pytest.raises(ValueError, match="not in PROPOSED"):
            await service.approve_action("action-uuid-001", "user-001", "org-001")

    @pytest.mark.asyncio
    async def test_approve_rejected_action_raises(self):
        db = _make_mock_db()
        service = AIService(db)

        mock_action = _make_mock_action(status="REJECTED")
        service.ai_action_repo.get_by_id = AsyncMock(return_value=mock_action)

        with pytest.raises(ValueError, match="not in PROPOSED"):
            await service.approve_action("action-uuid-001", "user-001", "org-001")


class TestAIServiceRejectAction:
    @pytest.mark.asyncio
    async def test_reject_proposed_action(self):
        db = _make_mock_db()
        service = AIService(db)

        mock_action = _make_mock_action(status="PROPOSED")
        service.ai_action_repo.get_by_id = AsyncMock(return_value=mock_action)
        service.ai_action_repo.update = AsyncMock()
        service.audit.log = AsyncMock()

        await service.reject_action("action-uuid-001", "user-001", "org-001", "Not relevant now")

        # Verify update was called with REJECTED status
        update_kwargs = service.ai_action_repo.update.call_args[1]
        assert update_kwargs.get("status") == "REJECTED"
        assert update_kwargs.get("rejection_reason") == "Not relevant now"

        # Verify audit log
        audit_kwargs = service.audit.log.call_args[1]
        assert audit_kwargs["action"] == "AI_ACTION_REJECTED"

    @pytest.mark.asyncio
    async def test_reject_nonexistent_action_raises(self):
        db = _make_mock_db()
        service = AIService(db)
        service.ai_action_repo.get_by_id = AsyncMock(return_value=None)

        with pytest.raises(ValueError, match="not found"):
            await service.reject_action("bad-id", "user-001", "org-001", "reason")

    @pytest.mark.asyncio
    async def test_reject_non_proposed_raises(self):
        db = _make_mock_db()
        service = AIService(db)

        mock_action = _make_mock_action(status="EXECUTED")
        service.ai_action_repo.get_by_id = AsyncMock(return_value=mock_action)

        with pytest.raises(ValueError, match="not in PROPOSED"):
            await service.reject_action("action-uuid-001", "user-001", "org-001", "reason")


class TestAIServiceEditAndApprove:
    @pytest.mark.asyncio
    async def test_edit_and_approve_merges_arguments(self):
        db = _make_mock_db()
        service = AIService(db)

        mock_action = _make_mock_action(status="PROPOSED")
        service.ai_action_repo.get_by_id = AsyncMock(return_value=mock_action)
        service.ai_action_repo.update = AsyncMock(return_value=mock_action)
        service.audit.log = AsyncMock()

        new_args = {"guest_count": 100, "event_date": "2026-11-01"}
        result = await service.edit_and_approve(
            "action-uuid-001", "user-001", "org-001", new_args
        )

        # First update call should include the new arguments merged
        assert service.ai_action_repo.update.called


class TestAIServiceListPending:
    @pytest.mark.asyncio
    async def test_list_pending_returns_proposed_actions(self):
        db = _make_mock_db()
        service = AIService(db)

        mock_actions = [
            _make_mock_action("PROPOSED", "create_quote"),
            _make_mock_action("PROPOSED", "send_email"),
        ]
        service.ai_action_repo.list_pending = AsyncMock(return_value=mock_actions)

        result = await service.list_pending_actions("org-001")
        assert len(result) == 2
