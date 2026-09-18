"""
Ollama HTTP client — wraps the local Ollama REST API.
Supports generate (single-turn) and chat (multi-turn) endpoints.
Model can be set at client construction time OR overridden per-call,
which enables the dual-model (Gemma analysis + Qwen tool-calling) pattern.
"""
import httpx
from app.core.config import settings
from app.core.logging import logger


class OllamaClient:
    def __init__(self, base_url: str = None, model: str = None):
        self.base_url = (base_url or settings.OLLAMA_BASE_URL).rstrip("/")
        self.default_model = model or settings.OLLAMA_ANALYSIS_MODEL
        self.client = httpx.AsyncClient(timeout=120.0)

    async def generate(
        self,
        prompt: str,
        system: str = None,
        format: str = "json",
        model: str = None,          # per-call model override
    ) -> dict:
        """
        POST /api/generate — single-turn generation.

        Args:
            model: Optional override for the model to use this call only.
                   Falls back to self.default_model if not specified.

        Returns:
            {
                "response": str,
                "total_duration": int (nanoseconds),
                "eval_count": int (tokens),
                "model_used": str,
            }
        """
        resolved_model = model or self.default_model
        payload = {
            "model": resolved_model,
            "prompt": prompt,
            "stream": False,
            "format": format,
            "options": {
                "temperature": 0.3,
                "num_predict": 2048,
            },
        }
        if system:
            payload["system"] = system

        try:
            response = await self.client.post(
                f"{self.base_url}/api/generate",
                json=payload,
            )
            response.raise_for_status()
            data = response.json()
            return {
                "response": data.get("response", ""),
                "total_duration": data.get("total_duration", 0),
                "eval_count": data.get("eval_count"),
                "model_used": resolved_model,
            }
        except httpx.ConnectError as exc:
            raise ConnectionError(
                f"Ollama is not running or unreachable at {self.base_url}. "
                f"Start it with: ollama serve"
            ) from exc
        except httpx.TimeoutException as exc:
            raise TimeoutError(
                f"Ollama request timed out after 120s for model '{resolved_model}'"
            ) from exc

    async def chat(
        self,
        messages: list[dict],
        system: str = None,
        format: str = "json",
        model: str = None,          # per-call model override
    ) -> dict:
        """
        POST /api/chat — multi-turn conversation.

        messages format: [{"role": "user", "content": "..."}, ...]
        """
        resolved_model = model or self.default_model
        payload = {
            "model": resolved_model,
            "messages": messages,
            "stream": False,
            "format": format,
            "options": {
                "temperature": 0.3,
                "num_predict": 2048,
            },
        }
        if system:
            payload["system"] = system

        try:
            response = await self.client.post(
                f"{self.base_url}/api/chat",
                json=payload,
            )
            response.raise_for_status()
            data = response.json()
            msg = data.get("message", {})
            return {
                "response": msg.get("content", ""),
                "total_duration": data.get("total_duration", 0),
                "eval_count": data.get("eval_count"),
                "model_used": resolved_model,
            }
        except httpx.ConnectError as exc:
            raise ConnectionError(
                f"Ollama is not running or unreachable at {self.base_url}."
            ) from exc
        except httpx.TimeoutException as exc:
            raise TimeoutError(
                f"Ollama chat request timed out after 120s for model '{resolved_model}'"
            ) from exc

    async def health_check(self) -> bool:
        """GET /api/tags → returns True if Ollama is reachable."""
        try:
            response = await self.client.get(f"{self.base_url}/api/tags", timeout=5.0)
            return response.status_code == 200
        except Exception:
            return False

    async def close(self):
        await self.client.aclose()
