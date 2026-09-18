import os
from typing import List, Union
from pydantic import AnyHttpUrl, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    PROJECT_NAME: str = "RestoOps Catering Revenue Agent"
    ENVIRONMENT: str = "development"
    DEBUG: bool = True
    API_V1_STR: str = "/api/v1"

    # Database
    POSTGRES_SERVER: str = "localhost"
    POSTGRES_PORT: int = 5432
    POSTGRES_USER: str = "restoops_user"
    POSTGRES_PASSWORD: str = "restoops_password_dev_123"
    POSTGRES_DB: str = "restoops_db"
    DATABASE_URL: str = (
        "postgresql+asyncpg://restoops_user:restoops_password_dev_123@localhost:5432/restoops_db"
    )

    # Redis & Celery
    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379
    REDIS_URL: str = "redis://localhost:6379/0"
    CELERY_BROKER_URL: str = "redis://localhost:6379/0"
    CELERY_RESULT_BACKEND: str = "redis://localhost:6379/1"

    # Security
    SECRET_KEY: str = "restoops-dev-secret-key-change-in-production-min-32-chars-long"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # Mail / SMTP
    SMTP_HOST: str = "localhost"
    SMTP_PORT: int = 1025
    SMTP_USER: str = ""
    SMTP_PASSWORD: str = ""
    EMAILS_FROM_EMAIL: str = "noreply@restoops.local"
    EMAILS_FROM_NAME: str = "RestoOps System"
    MAILPIT_HTTP_URL: str = "http://localhost:8025"

    # Gmail API (Phase 7+ — replaces Mailpit for real email delivery)
    GMAIL_CLIENT_ID: str = ""
    GMAIL_CLIENT_SECRET: str = ""
    GMAIL_REFRESH_TOKEN: str = ""
    GMAIL_SENDER_EMAIL: str = ""  # The Gmail address that was authorized

    @property
    def gmail_configured(self) -> bool:
        return bool(
            self.GMAIL_CLIENT_ID
            and self.GMAIL_CLIENT_SECRET
            and self.GMAIL_REFRESH_TOKEN
            and self.GMAIL_SENDER_EMAIL
        )

    # AI / Ollama
    OLLAMA_BASE_URL: str = "http://localhost:11434"
    # Gemma 3 4B — fast, excellent at language understanding, intent detection,
    # structured reasoning and conversation comprehension.
    OLLAMA_ANALYSIS_MODEL: str = "gemma3:4b"
    # Qwen 2.5 7B — fine-tuned for function/tool calling, produces highly
    # schema-conformant JSON tool suggestions.
    OLLAMA_TOOL_MODEL: str = "qwen2.5:7b"
    # Legacy alias kept for backward compat; defaults to analysis model
    OLLAMA_MODEL: str = "gemma3:4b"

    # API Public URL (needed for Exotel StatusCallback)
    API_URL: str = "http://localhost:8000"

    # Exotel (Phase 7 — replaces Twilio)
    EXOTEL_ACCOUNT_SID: str = ""
    EXOTEL_API_KEY: str = ""
    EXOTEL_API_TOKEN: str = ""
    EXOTEL_CALLER_ID: str = ""
    EXOTEL_SUBDOMAIN: str = "api.exotel.com"
    EXOTEL_WEBHOOK_SECRET: str = "change-me"

    @property
    def exotel_configured(self) -> bool:
        return bool(self.EXOTEL_API_KEY and self.EXOTEL_API_TOKEN and self.EXOTEL_ACCOUNT_SID)


    # CORS
    BACKEND_CORS_ORIGINS: List[str] = [
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:8000",
    ]

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )


settings = Settings()
