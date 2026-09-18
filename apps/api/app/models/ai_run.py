from sqlalchemy import ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base import Base, TimestampMixin, UUIDMixin


class AIRun(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "ai_runs"

    organization_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )

    # Which agent ran: CONVERSATION_ANALYZER, QUOTE_GENERATOR, LEAD_SCORER, etc.
    agent: Mapped[str] = mapped_column(String(50), nullable=False)
    # LLM model used: llama3.2, mistral, etc.
    model: Mapped[str] = mapped_column(String(100), nullable=False)

    conversation_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("conversations.id", ondelete="SET NULL"),
        nullable=True, index=True,
    )
    lead_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("leads.id", ondelete="SET NULL"),
        nullable=True, index=True,
    )

    input: Mapped[str] = mapped_column(Text, nullable=False)
    output: Mapped[str] = mapped_column(Text, nullable=False)
    structured_output: Mapped[dict | None] = mapped_column(JSONB, nullable=True)

    latency_ms: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    tokens_used: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # COMPLETED, FAILED, TIMEOUT
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="COMPLETED")
    error: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Relationships
    actions: Mapped[list["AIAction"]] = relationship(
        "AIAction", back_populates="ai_run", cascade="all, delete-orphan"
    )
