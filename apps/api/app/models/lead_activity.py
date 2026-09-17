from sqlalchemy import ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy import JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base import Base, TimestampMixin, UUIDMixin


class LeadActivity(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "lead_activities"

    lead_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("leads.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )
    user_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )

    # EMAIL_SENT | EMAIL_RECEIVED | CALL_MADE | QUOTE_SENT |
    # STATUS_CHANGED | NOTE_ADDED | VERIFIED | CSV_IMPORTED
    activity_type: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    activity_metadata: Mapped[dict | None] = mapped_column("metadata", JSON, nullable=True)

    lead: Mapped["Lead"] = relationship("Lead", back_populates="activities")
