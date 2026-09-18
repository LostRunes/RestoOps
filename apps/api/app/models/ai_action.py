from typing import TYPE_CHECKING
from sqlalchemy import ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy import DateTime
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base import Base, TimestampMixin, UUIDMixin

if TYPE_CHECKING:
    from app.models.ai_run import AIRun


class AIAction(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "ai_actions"

    ai_run_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("ai_runs.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )
    organization_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )

    # Tool to invoke: create_quote, send_email, update_lead, schedule_followup, etc.
    tool: Mapped[str] = mapped_column(String(100), nullable=False)
    arguments: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    result: Mapped[dict | None] = mapped_column(JSONB, nullable=True)

    # PROPOSED → APPROVED / REJECTED → EXECUTED / FAILED
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="PROPOSED", index=True)

    approved_by: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    approved_at: Mapped[DateTime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    executed_at: Mapped[DateTime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    rejection_reason: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Relationships
    ai_run: Mapped["AIRun"] = relationship("AIRun", back_populates="actions")
