"""
Conversation Analyzer Agent — analyzes inbound message threads and suggests actions.
"""
from __future__ import annotations
import time
from pydantic import ValidationError

from app.agents.base import BaseAgent, AgentResult
from app.agents.prompts import CONVERSATION_ANALYZER_SYSTEM
from app.agents.schemas import ConversationAnalysis
from app.integrations.ollama.client import OllamaClient
from app.core.logging import logger


class ConversationAgent(BaseAgent):
    def __init__(self, ollama_client: OllamaClient):
        super().__init__(ollama_client, "CONVERSATION_ANALYZER")

    def build_prompt(self, context: dict) -> str:
        """
        Build a structured prompt from lead + conversation context.

        Context keys:
            lead_company, lead_contact, lead_industry, lead_score, lead_priority
            channel
            messages: list of {"direction": "INBOUND|OUTBOUND", "date": str, "body": str}
        """
        lines = [
            f"Lead: {context.get('lead_company', 'Unknown')} ({context.get('lead_industry', 'Unknown industry')})",
            f"Contact: {context.get('lead_contact', 'Unknown')}",
            f"Score: {context.get('lead_score', 0)}/100 ({context.get('lead_priority', 'MEDIUM')})",
            f"Channel: {context.get('channel', 'EMAIL')}",
            "",
            "Conversation:",
        ]

        for msg in context.get("messages", []):
            direction = msg.get("direction", "UNKNOWN")
            date = msg.get("date", "")
            body = msg.get("body", "").strip()
            label = "OUTBOUND" if direction == "OUTBOUND" else "INBOUND"
            lines.append(f"[{label}] {date}: {body}")

        lines.append("")
        lines.append("Analyze this conversation and suggest actions.")
        return "\n".join(lines)

    async def analyze(
        self,
        context: dict,
    ) -> AgentResult:
        """
        Run the full conversation analysis:
        1. Build context prompt
        2. Call Ollama with system prompt (JSON mode)
        3. Parse structured response into ConversationAnalysis
        4. Return AgentResult with all metadata
        """
        prompt = self.build_prompt(context)

        start_ms = int(time.time() * 1000)
        status = "COMPLETED"
        error = None
        raw_output = ""
        structured = {}
        tokens = None
        analysis = None

        try:
            result = await self.ollama.generate(
                prompt=prompt,
                system=CONVERSATION_ANALYZER_SYSTEM,
                format="json",
            )
            raw_output = result["response"]
            tokens = result.get("eval_count")

            parsed = self.parse_response(raw_output)
            structured = parsed

            try:
                analysis = ConversationAnalysis(**parsed)
            except (ValidationError, TypeError) as ve:
                logger.warning(
                    "conversation_agent_validation_error",
                    error=str(ve),
                    parsed=str(parsed)[:300],
                )
                # Return partial result rather than failing entirely
                analysis = None

        except ConnectionError as exc:
            status = "FAILED"
            error = str(exc)
            logger.error("conversation_agent_ollama_connection_error", error=error)
        except TimeoutError as exc:
            status = "TIMEOUT"
            error = str(exc)
            logger.error("conversation_agent_ollama_timeout", error=error)
        except Exception as exc:
            status = "FAILED"
            error = str(exc)
            logger.error("conversation_agent_unexpected_error", error=error)

        latency_ms = int(time.time() * 1000) - start_ms

        return AgentResult(
            agent_name=self.name,
            raw_output=raw_output,
            structured_output=structured,
            latency_ms=latency_ms,
            tokens_used=tokens,
            status=status,
            error=error,
            analysis=analysis,
        )
