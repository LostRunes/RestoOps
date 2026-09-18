from typing import TYPE_CHECKING
from datetime import datetime
from sqlalchemy import DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base import Base, TimestampMixin, UUIDMixin

if TYPE_CHECKING:
    from app.models.call_event import CallEvent


class Call(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "calls"

    organization_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )
    restaurant_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("restaurants.id", ondelete="SET NULL"),
        nullable=True,
    )
    lead_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("leads.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )
    conversation_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("conversations.id", ondelete="SET NULL"),
        nullable=True,
    )

    # EXOTEL or WEBRTC
    provider: Mapped[str] = mapped_column(String(20), nullable=False)

    # OUTBOUND or INBOUND
    direction: Mapped[str] = mapped_column(String(10), nullable=False, default="OUTBOUND")

    from_number: Mapped[str | None] = mapped_column(String(50), nullable=True)
    to_number: Mapped[str | None] = mapped_column(String(50), nullable=True)

    # INITIATED → RINGING → IN_PROGRESS → COMPLETED → FAILED → NO_ANSWER → BUSY → CANCELLED
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="INITIATED", index=True)

    initiated_by: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )

    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    answered_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    ended_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    duration_seconds: Mapped[int | None] = mapped_column(Integer, nullable=True)

    recording_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    # Exotel call SID (was twilio_call_sid in original plan)
    exotel_call_sid: Mapped[str | None] = mapped_column(
        String(100), nullable=True, unique=True, index=True
    )

    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Relationships
    events: Mapped[list["CallEvent"]] = relationship(
        "CallEvent", back_populates="call", cascade="all, delete-orphan",
        order_by="CallEvent.created_at",
    )
