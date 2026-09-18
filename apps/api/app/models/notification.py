from datetime import datetime
from sqlalchemy import Boolean, DateTime, ForeignKey, Index, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column
from app.db.base import Base, TimestampMixin, UUIDMixin


class Notification(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "notifications"

    organization_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )
    user_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )

    # Notification type — see EventType enum
    # LEAD_REPLIED, QUOTE_REQUESTED, QUOTE_ACCEPTED, QUOTE_REJECTED, QUOTE_EXPIRED
    # CALL_COMPLETED, HIGH_VALUE_LEAD, CAMPAIGN_COMPLETED, FOLLOWUP_DUE
    # AI_ACTION_PROPOSED, AI_ACTION_APPROVED, AI_ACTION_REJECTED
    # ORDER_CREATED, VERIFICATION_COMPLETED, LEAD_IMPORTED, LEAD_CREATED, LEAD_VERIFIED
    type: Mapped[str] = mapped_column(String(50), nullable=False)

    title: Mapped[str] = mapped_column(String(255), nullable=False)
    body: Mapped[str] = mapped_column(Text, nullable=False)

    # The related domain entity (so frontend can deep-link)
    entity_type: Mapped[str | None] = mapped_column(String(50), nullable=True)
    entity_id: Mapped[str | None] = mapped_column(String(36), nullable=True)

    # LOW | NORMAL | HIGH | URGENT
    priority: Mapped[str] = mapped_column(String(20), nullable=False, default="NORMAL")

    is_read: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    read_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    notification_metadata: Mapped[dict | None] = mapped_column("metadata", JSONB, nullable=True)

    __table_args__ = (
        # Fast unread lookup per user
        Index("ix_notifications_user_unread", "user_id", "is_read"),
        # Sorted feed per org
        Index("ix_notifications_org_created", "organization_id", "created_at"),
    )
