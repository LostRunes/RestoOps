"""
Config & Settings Tests — validates model settings are correct after the dual-model change.
"""
import pytest
from app.core.config import settings


class TestSettings:
    def test_analysis_model_is_gemma(self):
        assert "gemma" in settings.OLLAMA_ANALYSIS_MODEL.lower(), (
            f"Expected Gemma as analysis model, got: {settings.OLLAMA_ANALYSIS_MODEL}"
        )

    def test_tool_model_is_qwen(self):
        assert "qwen" in settings.OLLAMA_TOOL_MODEL.lower(), (
            f"Expected Qwen as tool model, got: {settings.OLLAMA_TOOL_MODEL}"
        )

    def test_models_are_different(self):
        assert settings.OLLAMA_ANALYSIS_MODEL != settings.OLLAMA_TOOL_MODEL, (
            "Analysis and tool models should be different"
        )

    def test_ollama_url_set(self):
        assert settings.OLLAMA_BASE_URL.startswith("http"), (
            f"OLLAMA_BASE_URL looks malformed: {settings.OLLAMA_BASE_URL}"
        )

    def test_database_url_set(self):
        assert "postgresql" in settings.DATABASE_URL

    def test_redis_url_set(self):
        assert settings.REDIS_URL.startswith("redis://")

    def test_secret_key_not_empty(self):
        assert len(settings.SECRET_KEY) >= 32, "SECRET_KEY too short"
