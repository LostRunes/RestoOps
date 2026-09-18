"""
ConversationAgent Integration Tests (Mocked Ollama)
Tests the full two-pass analysis flow without real Ollama.
"""
import json
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from app.agents.conversation_agent import ConversationAgent
from app.integrations.ollama.client import OllamaClient


SAMPLE_CONTEXT = {
    "lead_id": "lead-uuid-123",
    "lead_email": "john@acmecorp.com",
    "lead_company": "Acme Corp",
    "lead_contact": "John Smith",
    "lead_industry": "Corporate",
    "lead_score": 72,
    "lead_priority": "HIGH",
    "channel": "EMAIL",
    "messages": [
        {
            "direction": "OUTBOUND",
            "date": "2026-09-10 09:00",
            "body": "Hi John, we'd love to help with your upcoming event!",
        },
        {
            "direction": "INBOUND",
            "date": "2026-09-11 14:23",
            "body": (
                "Hi! Yes, we need catering for about 80 people. "
                "The event is October 15th, a corporate lunch. "
                "Budget is around $6,000. Some guests are vegan. Can you send a quote?"
            ),
        },
    ],
}

PASS1_RESPONSE = {
    "intent": "NEEDS_QUOTE",
    "sentiment": "POSITIVE",
    "urgency": "HIGH",
    "guest_count": 80,
    "event_date": "2026-10-15",
    "event_type": "corporate lunch",
    "budget_mentioned": "$6,000",
    "dietary_requirements": ["vegan"],
    "key_points": ["80 guests", "October 15th", "Budget ~$6k"],
    "suggested_lead_status": "QUALIFIED",
}

PASS2_RESPONSE = {
    "suggested_actions": [
        {
            "tool": "create_quote",
            "description": "Create a catering quote for 80 guests on October 15th",
            "arguments": {
                "lead_id": "lead-uuid-123",
                "guest_count": 80,
                "event_date": "2026-10-15",
                "event_type": "corporate lunch",
            },
            "confidence": 0.95,
            "requires_approval": True,
        },
        {
            "tool": "update_lead",
            "description": "Update lead status to QUALIFIED",
            "arguments": {
                "lead_id": "lead-uuid-123",
                "pipeline_status": "QUALIFIED",
            },
            "confidence": 0.88,
            "requires_approval": True,
        },
    ]
}


def _make_mock_ollama(pass1_data, pass2_data):
    """Build a mock OllamaClient that returns canned responses for each pass."""
    client = MagicMock(spec=OllamaClient)
    call_count = [0]

    async def mock_generate(prompt, system=None, format="json", model=None):
        call_count[0] += 1
        if call_count[0] == 1:
            return {
                "response": json.dumps(pass1_data),
                "total_duration": 1_200_000_000,
                "eval_count": 110,
                "model_used": "gemma3:4b",
            }
        else:
            return {
                "response": json.dumps(pass2_data),
                "total_duration": 900_000_000,
                "eval_count": 85,
                "model_used": "qwen2.5:7b",
            }

    client.generate = mock_generate
    return client


class TestConversationAgentTwoPass:
    @pytest.mark.asyncio
    async def test_successful_two_pass_analysis(self):
        mock_ollama = _make_mock_ollama(PASS1_RESPONSE, PASS2_RESPONSE)
        agent = ConversationAgent(mock_ollama)
        result = await agent.analyze(SAMPLE_CONTEXT)

        assert result.status == "COMPLETED"
        assert result.error is None
        assert result.latency_ms >= 0
        assert result.tokens_used == 195  # 110 + 85

    @pytest.mark.asyncio
    async def test_analysis_extracts_intent(self):
        mock_ollama = _make_mock_ollama(PASS1_RESPONSE, PASS2_RESPONSE)
        agent = ConversationAgent(mock_ollama)
        result = await agent.analyze(SAMPLE_CONTEXT)

        assert result.structured_output["intent"] == "NEEDS_QUOTE"
        assert result.structured_output["guest_count"] == 80
        assert result.structured_output["event_date"] == "2026-10-15"
        assert result.structured_output["budget_mentioned"] == "$6,000"

    @pytest.mark.asyncio
    async def test_analysis_extracts_tool_suggestions(self):
        mock_ollama = _make_mock_ollama(PASS1_RESPONSE, PASS2_RESPONSE)
        agent = ConversationAgent(mock_ollama)
        result = await agent.analyze(SAMPLE_CONTEXT)

        actions = result.structured_output.get("suggested_actions", [])
        assert len(actions) == 2
        tools = [a["tool"] for a in actions]
        assert "create_quote" in tools
        assert "update_lead" in tools

    @pytest.mark.asyncio
    async def test_models_logged_in_output(self):
        mock_ollama = _make_mock_ollama(PASS1_RESPONSE, PASS2_RESPONSE)
        agent = ConversationAgent(mock_ollama)
        result = await agent.analyze(SAMPLE_CONTEXT)

        models = result.structured_output.get("_models", {})
        assert models.get("analysis") == "gemma3:4b"
        assert models.get("tools") == "qwen2.5:7b"

    @pytest.mark.asyncio
    async def test_pydantic_validation_succeeds(self):
        mock_ollama = _make_mock_ollama(PASS1_RESPONSE, PASS2_RESPONSE)
        agent = ConversationAgent(mock_ollama)
        result = await agent.analyze(SAMPLE_CONTEXT)

        # analysis attribute should be a ConversationAnalysis object
        assert result.analysis is not None
        assert result.analysis.intent == "NEEDS_QUOTE"
        assert result.analysis.guest_count == 80

    @pytest.mark.asyncio
    async def test_ollama_connection_error_returns_failed(self):
        client = MagicMock(spec=OllamaClient)
        client.generate = AsyncMock(side_effect=ConnectionError("Ollama not running"))

        agent = ConversationAgent(client)
        result = await agent.analyze(SAMPLE_CONTEXT)

        assert result.status == "FAILED"
        assert result.error is not None
        assert "Ollama" in result.error or "not running" in result.error

    @pytest.mark.asyncio
    async def test_ollama_timeout_returns_timeout(self):
        client = MagicMock(spec=OllamaClient)
        client.generate = AsyncMock(side_effect=TimeoutError("Request timed out"))

        agent = ConversationAgent(client)
        result = await agent.analyze(SAMPLE_CONTEXT)

        assert result.status == "TIMEOUT"

    @pytest.mark.asyncio
    async def test_malformed_pass1_json_still_completes(self):
        """If pass1 returns garbage JSON, pass2 should still run with empty data."""
        client = MagicMock(spec=OllamaClient)
        call_count = [0]

        async def mock_generate(prompt, system=None, format="json", model=None):
            call_count[0] += 1
            if call_count[0] == 1:
                return {"response": "NOT JSON AT ALL <<<>>>", "eval_count": 10, "total_duration": 0}
            else:
                return {"response": json.dumps(PASS2_RESPONSE), "eval_count": 50, "total_duration": 0}

        client.generate = mock_generate
        agent = ConversationAgent(client)
        result = await agent.analyze(SAMPLE_CONTEXT)

        # Should not crash — just return partial results
        assert result.status == "COMPLETED"
        # Pass1 data will be empty dict, but no exception
        assert isinstance(result.structured_output, dict)

    def test_build_prompt_includes_lead_info(self):
        agent = ConversationAgent(MagicMock())
        prompt = agent.build_prompt(SAMPLE_CONTEXT)

        assert "Acme Corp" in prompt
        assert "John Smith" in prompt
        assert "Corporate" in prompt
        assert "HIGH" in prompt
        assert "INBOUND" in prompt
        assert "OUTBOUND" in prompt

    def test_build_prompt_includes_full_conversation(self):
        agent = ConversationAgent(MagicMock())
        prompt = agent.build_prompt(SAMPLE_CONTEXT)

        assert "80 people" in prompt
        assert "October 15th" in prompt
        assert "vegan" in prompt
