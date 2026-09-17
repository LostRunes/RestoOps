from datetime import datetime
from sqlalchemy import DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base import Base, TimestampMixin, UUIDMixin


class Conversation(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "conversations"

    organization_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )
    restaurant_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("restaurants.id", ondelete="SET NULL"),
        nullable=True, index=True,
    )
    lead_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("leads.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )

    channel: Mapped[str] = mapped_column(String(20), default="EMAIL", nullable=False)  # EMAIL, SMS, VOICE, WEBRTC
    status: Mapped[str] = mapped_column(String(20), default="OPEN", nullable=False)   # OPEN, CLOSED, ARCHIVED

    subject: Mapped[str | None] = mapped_column(String(500), nullable=True)
    message_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    last_message_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    lead: Mapped["Lead"] = relationship("Lead")
    messages: Mapped[list["Message"]] = relationship(
        "Message", back_populates="conversation", cascade="all, delete-orphan", order_by="Message.created_at"
    )
