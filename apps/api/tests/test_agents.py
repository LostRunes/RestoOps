"""
Phase 5 — Agent Schema & Tool Registry Tests
Pure unit tests, no DB or Ollama needed.
"""
import pytest
from app.agents.schemas import ConversationAnalysis, SuggestedAction
from app.agents.base import BaseAgent
from app.agents.tools import ToolRegistry
from app.agents.prompts import ANALYSIS_SYSTEM, TOOL_SYSTEM


class TestConversationAnalysisSchema:
    def test_minimal_valid_schema(self):
        analysis = ConversationAnalysis(
            intent="NEEDS_QUOTE",
            sentiment="POSITIVE",
            urgency="HIGH",
            key_points=["Guest count: 80", "Date: October 15th"],
        )
        assert analysis.intent == "NEEDS_QUOTE"
        assert analysis.guest_count is None
        assert analysis.suggested_actions == []

    def test_full_schema(self):
        action = SuggestedAction(
            tool="create_quote",
            description="Create a quote for 80 guests",
            arguments={"lead_id": "abc", "guest_count": 80},
            confidence=0.92,
        )
        analysis = ConversationAnalysis(
            intent="NEEDS_QUOTE",
            sentiment="POSITIVE",
            urgency="HIGH",
            guest_count=80,
            event_date="2026-10-15",
            event_type="corporate lunch",
            budget_mentioned="$6000",
            dietary_requirements=["vegan", "gluten-free"],
            key_points=["80 guests", "October 15th"],
            suggested_lead_status="QUALIFIED",
            suggested_actions=[action],
        )
        assert analysis.guest_count == 80
        assert len(analysis.suggested_actions) == 1
        assert analysis.suggested_actions[0].confidence == 0.92

    def test_suggested_action_confidence_bounds(self):
        with pytest.raises(Exception):
            SuggestedAction(
                tool="send_email",
                description="Test",
                arguments={},
                confidence=1.5,   # Out of bounds > 1.0
            )

    def test_suggested_action_confidence_zero(self):
        action = SuggestedAction(
            tool="create_task",
            description="Create task",
            arguments={},
            confidence=0.0,
        )
        assert action.confidence == 0.0

    def test_requires_approval_default_true(self):
        action = SuggestedAction(
            tool="update_lead",
            description="Update status",
            arguments={},
            confidence=0.8,
        )
        assert action.requires_approval is True


class TestBaseAgentJsonParsing:
    """Test the parse_response fallback logic."""

    class _DummyAgent(BaseAgent):
        def build_prompt(self, context): return ""

    def setup_method(self):
        self.agent = self._DummyAgent(None, "TEST")

    def test_clean_json(self):
        raw = '{"intent": "NEEDS_QUOTE", "sentiment": "POSITIVE"}'
        result = self.agent.parse_response(raw)
        assert result["intent"] == "NEEDS_QUOTE"

    def test_json_with_prose_before(self):
        """LLM sometimes outputs prose before the JSON block."""
        raw = 'Here is the analysis:\n{"intent": "INTERESTED", "sentiment": "NEUTRAL"}\n'
        result = self.agent.parse_response(raw)
        assert result["intent"] == "INTERESTED"

    def test_empty_string_returns_empty_dict(self):
        result = self.agent.parse_response("")
        assert result == {}

    def test_completely_broken_json_returns_empty(self):
        result = self.agent.parse_response("This is just prose, no JSON at all.")
        assert result == {}

    def test_nested_json(self):
        raw = '{"intent": "NEEDS_QUOTE", "suggested_actions": [{"tool": "create_quote"}]}'
        result = self.agent.parse_response(raw)
        assert result["suggested_actions"][0]["tool"] == "create_quote"


class TestToolRegistry:
    def test_all_tools_registered(self):
        tools = ToolRegistry.list_tools()
        expected = {
            "create_quote", "send_email", "update_lead",
            "schedule_followup", "create_task", "add_suppression"
        }
        assert expected.issubset(set(tools)), f"Missing tools: {expected - set(tools)}"

    def test_get_existing_tool(self):
        tool = ToolRegistry.get_tool("create_quote")
        assert tool is not None
        assert tool["requires_approval"] is True

    def test_get_nonexistent_tool(self):
        tool = ToolRegistry.get_tool("does_not_exist")
        assert tool is None

    @pytest.mark.asyncio
    async def test_execute_unknown_tool_raises(self):
        with pytest.raises(ValueError, match="Unknown tool"):
            await ToolRegistry.execute("nonexistent_tool")

    @pytest.mark.asyncio
    async def test_execute_create_quote(self):
        result = await ToolRegistry.execute(
            "create_quote",
            lead_id="test-123",
            guest_count=50,
            event_date="2026-12-01",
            event_type="wedding",
        )
        assert result["lead_id"] == "test-123"
        assert result["guest_count"] == 50

    @pytest.mark.asyncio
    async def test_execute_send_email(self):
        result = await ToolRegistry.execute(
            "send_email",
            lead_id="test-456",
            subject="Following up on your catering inquiry",
            body="Thank you for your interest...",
        )
        assert result["status"] == "queued"
        assert result["lead_id"] == "test-456"

    @pytest.mark.asyncio
    async def test_execute_add_suppression(self):
        result = await ToolRegistry.execute(
            "add_suppression",
            email="optout@example.com",
            reason="opt_out",
        )
        assert result["status"] == "suppressed"
        assert result["email"] == "optout@example.com"

    @pytest.mark.asyncio
    async def test_execute_update_lead(self):
        result = await ToolRegistry.execute(
            "update_lead",
            lead_id="test-789",
            pipeline_status="QUALIFIED",
            priority="HIGH",
        )
        assert result["pipeline_status"] == "QUALIFIED"

    @pytest.mark.asyncio
    async def test_execute_schedule_followup(self):
        result = await ToolRegistry.execute(
            "schedule_followup",
            lead_id="test-001",
            follow_up_date="2026-10-01",
            note="Follow up on quote",
        )
        assert result["status"] == "scheduled"

    @pytest.mark.asyncio
    async def test_execute_create_task(self):
        result = await ToolRegistry.execute(
            "create_task",
            lead_id="test-002",
            title="Call client about dietary requirements",
            description="They mentioned vegan options needed",
        )
        assert result["status"] == "created"


class TestPrompts:
    def test_analysis_system_prompt_exists(self):
        assert len(ANALYSIS_SYSTEM) > 100
        assert "intent" in ANALYSIS_SYSTEM
        assert "sentiment" in ANALYSIS_SYSTEM
        assert "JSON" in ANALYSIS_SYSTEM

    def test_tool_system_prompt_exists(self):
        assert len(TOOL_SYSTEM) > 100
        assert "create_quote" in TOOL_SYSTEM
        assert "send_email" in TOOL_SYSTEM
        assert "requires_approval" in TOOL_SYSTEM
        assert "lead_id" in TOOL_SYSTEM

    def test_prompts_are_separate(self):
        # Ensure the two prompts serve different purposes
        assert ANALYSIS_SYSTEM != TOOL_SYSTEM
        # Tool system should NOT define intent/sentiment (that's analysis)
        assert "\"intent\":" not in TOOL_SYSTEM
