"""
Conversation Analyzer Agent — two-pass architecture.

Pass 1 (Gemma 3):  Understand the conversation → extract intent, sentiment,
                   event details, key points, suggested lead status.
Pass 2 (Qwen 2.5): Given the analysis → decide which CRM tools to call
                   and with what structured arguments.

This separation gives each model its optimal task:
- Gemma excels at natural language comprehension and structured reasoning.
- Qwen excels at function/tool calling with schema-conformant JSON outputs.
"""
from __future__ import annotations
import json
import time

from pydantic import ValidationError

from app.agents.base import BaseAgent, AgentResult
from app.agents.prompts import ANALYSIS_SYSTEM, TOOL_SYSTEM
from app.agents.schemas import ConversationAnalysis, SuggestedAction
from app.integrations.ollama.client import OllamaClient
from app.core.config import settings
from app.core.logging import logger


class ConversationAgent(BaseAgent):
    def __init__(self, ollama_client: OllamaClient):
        super().__init__(ollama_client, "CONVERSATION_ANALYZER")

    def build_prompt(self, context: dict) -> str:
        """
        Build the conversation thread prompt shared by both passes.

        Context keys:
            lead_company, lead_contact, lead_industry, lead_score, lead_priority
            lead_id, lead_email, channel
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
        return "\n".join(lines)

    def _build_tool_prompt(self, analysis: dict, context: dict) -> str:
        """Build the prompt for Pass 2 (Qwen tool suggestion)."""
        lead_id = context.get("lead_id", "unknown")
        lead_email = context.get("lead_email", "")
        lines = [
            f"Lead ID: {lead_id}",
            f"Lead email: {lead_email}",
            "",
            "Conversation analysis from Pass 1:",
            json.dumps(analysis, indent=2),
            "",
            "Based on this analysis, which CRM tools should be called?",
            f"Use lead_id=\"{lead_id}\" in all arguments.",
        ]
        return "\n".join(lines)

    async def analyze(self, context: dict) -> AgentResult:
        """
        Two-pass conversation analysis:
        1. Gemma → understand the conversation (analysis)
        2. Qwen  → suggest tools (tool_suggestions)

        Returns an AgentResult with the merged structured_output.
        """
        conversation_prompt = self.build_prompt(context)

        start_ms = int(time.time() * 1000)
        status = "COMPLETED"
        error = None
        raw_output = ""
        structured = {}
        tokens_total = 0
        analysis_obj = None

        try:
            # ── Pass 1: Gemma — conversation understanding ────────────────────
            logger.info(
                "conversation_agent_pass1_start",
                model=settings.OLLAMA_ANALYSIS_MODEL,
            )
            pass1_result = await self.ollama.generate(
                prompt=conversation_prompt + "\nAnalyze this conversation.",
                system=ANALYSIS_SYSTEM,
                format="json",
                model=settings.OLLAMA_ANALYSIS_MODEL,
            )
            raw_pass1 = pass1_result["response"]
            tokens_total += pass1_result.get("eval_count") or 0
            analysis_data = self.parse_response(raw_pass1)

            logger.info(
                "conversation_agent_pass1_done",
                model=settings.OLLAMA_ANALYSIS_MODEL,
                intent=analysis_data.get("intent"),
                latency_ns=pass1_result.get("total_duration", 0),
            )

            # ── Pass 2: Qwen — tool suggestions ──────────────────────────────
            logger.info(
                "conversation_agent_pass2_start",
                model=settings.OLLAMA_TOOL_MODEL,
            )
            tool_prompt = self._build_tool_prompt(analysis_data, context)
            pass2_result = await self.ollama.generate(
                prompt=tool_prompt,
                system=TOOL_SYSTEM,
                format="json",
                model=settings.OLLAMA_TOOL_MODEL,
            )
            raw_pass2 = pass2_result["response"]
            tokens_total += pass2_result.get("eval_count") or 0
            tool_data = self.parse_response(raw_pass2)

            logger.info(
                "conversation_agent_pass2_done",
                model=settings.OLLAMA_TOOL_MODEL,
                actions=len(tool_data.get("suggested_actions", [])),
                latency_ns=pass2_result.get("total_duration", 0),
            )

            # ── Merge both passes into final structured output ────────────────
            raw_output = json.dumps({
                "pass1_analysis": raw_pass1,
                "pass2_tools": raw_pass2,
            })
            structured = {
                **analysis_data,
                "suggested_actions": tool_data.get("suggested_actions", []),
                "_models": {
                    "analysis": settings.OLLAMA_ANALYSIS_MODEL,
                    "tools": settings.OLLAMA_TOOL_MODEL,
                },
            }

            # Validate with Pydantic
            try:
                analysis_obj = ConversationAnalysis(**structured)
            except (ValidationError, TypeError) as ve:
                logger.warning(
                    "conversation_agent_validation_warning",
                    error=str(ve),
                    structured=str(structured)[:300],
                )
                # Partial result — still usable, just not schema-validated
                analysis_obj = None

        except ConnectionError as exc:
            status = "FAILED"
            error = str(exc)
            logger.error("conversation_agent_connection_error", error=error)
        except TimeoutError as exc:
            status = "TIMEOUT"
            error = str(exc)
            logger.error("conversation_agent_timeout", error=error)
        except Exception as exc:
            status = "FAILED"
            error = str(exc)
            logger.error("conversation_agent_unexpected_error", error=error, exc_info=True)

        latency_ms = int(time.time() * 1000) - start_ms

        return AgentResult(
            agent_name=self.name,
            raw_output=raw_output,
            structured_output=structured,
            latency_ms=latency_ms,
            tokens_used=tokens_total if tokens_total > 0 else None,
            status=status,
            error=error,
            analysis=analysis_obj,
        )
