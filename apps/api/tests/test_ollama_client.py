"""
Ollama Client Tests — mock HTTP responses, no real Ollama needed.
Tests model override, error handling, and response parsing.
"""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from app.integrations.ollama.client import OllamaClient


@pytest.fixture
def client():
    return OllamaClient(base_url="http://localhost:11434", model="gemma3:4b")


class TestOllamaClientGenerate:
    @pytest.mark.asyncio
    async def test_successful_generate(self, client):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "response": '{"intent": "NEEDS_QUOTE"}',
            "total_duration": 1_500_000_000,
            "eval_count": 142,
        }
        mock_response.raise_for_status = MagicMock()

        with patch.object(client.client, "post", new=AsyncMock(return_value=mock_response)):
            result = await client.generate(prompt="Analyze this.")
        
        assert result["response"] == '{"intent": "NEEDS_QUOTE"}'
        assert result["eval_count"] == 142
        assert result["model_used"] == "gemma3:4b"

    @pytest.mark.asyncio
    async def test_per_call_model_override(self, client):
        """Model override should override the default for just this call."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "response": "{}",
            "total_duration": 0,
            "eval_count": 10,
        }
        mock_response.raise_for_status = MagicMock()

        captured_payload = {}
        async def mock_post(url, json=None, **kwargs):
            captured_payload.update(json or {})
            return mock_response

        with patch.object(client.client, "post", new=mock_post):
            result = await client.generate(prompt="Test.", model="qwen2.5:7b")
        
        assert captured_payload["model"] == "qwen2.5:7b"
        assert result["model_used"] == "qwen2.5:7b"

    @pytest.mark.asyncio
    async def test_default_model_used_when_no_override(self, client):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"response": "{}", "total_duration": 0, "eval_count": 5}
        mock_response.raise_for_status = MagicMock()

        captured = {}
        async def mock_post(url, json=None, **kwargs):
            captured.update(json or {})
            return mock_response

        with patch.object(client.client, "post", new=mock_post):
            await client.generate(prompt="Test.")
        
        assert captured["model"] == "gemma3:4b"

    @pytest.mark.asyncio
    async def test_connection_error_raises_connection_error(self, client):
        import httpx
        with patch.object(client.client, "post", new=AsyncMock(side_effect=httpx.ConnectError("refused"))):
            with pytest.raises(ConnectionError, match="not running"):
                await client.generate(prompt="Test.")

    @pytest.mark.asyncio
    async def test_timeout_raises_timeout_error(self, client):
        import httpx
        with patch.object(client.client, "post", new=AsyncMock(side_effect=httpx.TimeoutException("timeout"))):
            with pytest.raises(TimeoutError, match="timed out"):
                await client.generate(prompt="Test.")

    @pytest.mark.asyncio
    async def test_system_prompt_included_when_given(self, client):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"response": "{}", "total_duration": 0, "eval_count": 1}
        mock_response.raise_for_status = MagicMock()

        captured = {}
        async def mock_post(url, json=None, **kwargs):
            captured.update(json or {})
            return mock_response

        with patch.object(client.client, "post", new=mock_post):
            await client.generate(prompt="Test.", system="You are a helpful assistant.")

        assert captured.get("system") == "You are a helpful assistant."

    @pytest.mark.asyncio
    async def test_system_prompt_omitted_when_none(self, client):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"response": "{}", "total_duration": 0, "eval_count": 1}
        mock_response.raise_for_status = MagicMock()

        captured = {}
        async def mock_post(url, json=None, **kwargs):
            captured.update(json or {})
            return mock_response

        with patch.object(client.client, "post", new=mock_post):
            await client.generate(prompt="Test.", system=None)

        assert "system" not in captured


class TestOllamaHealthCheck:
    @pytest.mark.asyncio
    async def test_health_check_returns_true_on_200(self, client):
        mock_response = MagicMock()
        mock_response.status_code = 200
        with patch.object(client.client, "get", new=AsyncMock(return_value=mock_response)):
            assert await client.health_check() is True

    @pytest.mark.asyncio
    async def test_health_check_returns_false_on_error(self, client):
        import httpx
        with patch.object(client.client, "get", new=AsyncMock(side_effect=httpx.ConnectError("refused"))):
            assert await client.health_check() is False

    @pytest.mark.asyncio
    async def test_health_check_returns_false_on_non_200(self, client):
        mock_response = MagicMock()
        mock_response.status_code = 500
        with patch.object(client.client, "get", new=AsyncMock(return_value=mock_response)):
            assert await client.health_check() is False
