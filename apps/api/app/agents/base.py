"""
Base agent class — all agents inherit from this.
"""
from __future__ import annotations
import json
from dataclasses import dataclass, field
from app.integrations.ollama.client import OllamaClient
from app.agents.schemas import ConversationAnalysis
from app.core.logging import logger


@dataclass
class AgentResult:
    agent_name: str
    raw_output: str
    structured_output: dict
    latency_ms: int
    tokens_used: int | None
    status: str   # COMPLETED | FAILED | TIMEOUT
    error: str | None = None
    analysis: ConversationAnalysis | None = None


class BaseAgent:
    def __init__(self, ollama_client: OllamaClient, name: str):
        self.ollama = ollama_client
        self.name = name

    def build_prompt(self, context: dict) -> str:
        """Override in subclasses to build agent-specific prompt."""
        raise NotImplementedError

    def parse_response(self, raw_response: str) -> dict:
        """
        Parse JSON from LLM response. Handles malformed JSON gracefully
        by attempting to extract the first JSON object found in the string.
        """
        # Try direct parse first
        try:
            return json.loads(raw_response)
        except json.JSONDecodeError:
            pass

        # Try to find JSON object boundaries in case the model added prose
        start = raw_response.find("{")
        end = raw_response.rfind("}") + 1
        if start != -1 and end > start:
            try:
                return json.loads(raw_response[start:end])
            except json.JSONDecodeError:
                pass

        logger.warning("agent_json_parse_failed", agent=self.name, raw=raw_response[:200])
        return {}
