from datetime import datetime
from sqlalchemy import DateTime, ForeignKey, Index, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base import Base, TimestampMixin, UUIDMixin


class CampaignLead(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "campaign_leads"

    campaign_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("campaigns.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )
    lead_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("leads.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )

    current_step: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    # PENDING, IN_PROGRESS, COMPLETED, REPLIED, BOUNCED, UNSUBSCRIBED, SKIPPED
    status: Mapped[str] = mapped_column(String(20), default="PENDING", nullable=False, index=True)

    next_step_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True, index=True)

    campaign: Mapped["Campaign"] = relationship("Campaign", back_populates="campaign_leads")
    lead: Mapped["Lead"] = relationship("Lead")

    __table_args__ = (
        UniqueConstraint("campaign_id", "lead_id", name="uq_campaign_lead"),
        Index("idx_campaign_lead_status", "campaign_id", "status"),
    )
