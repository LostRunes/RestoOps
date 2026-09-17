from datetime import datetime
from sqlalchemy import DateTime, ForeignKey, String, Text, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base import Base, TimestampMixin, UUIDMixin


class Campaign(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "campaigns"

    organization_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )
    restaurant_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("restaurants.id", ondelete="SET NULL"),
        nullable=True, index=True,
    )

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    # DRAFT, ACTIVE, PAUSED, COMPLETED, CANCELLED
    status: Mapped[str] = mapped_column(String(20), default="DRAFT", nullable=False, index=True)

    # Target lead filters (JSON)
    target_filters: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    created_by: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    steps: Mapped[list["CampaignStep"]] = relationship(
        "CampaignStep", back_populates="campaign", cascade="all, delete-orphan", order_by="CampaignStep.step_number"
    )
    campaign_leads: Mapped[list["CampaignLead"]] = relationship(
        "CampaignLead", back_populates="campaign", cascade="all, delete-orphan"
    )
