from sqlalchemy import ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base import Base, TimestampMixin, UUIDMixin


class CampaignStep(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "campaign_steps"

    campaign_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("campaigns.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )

    step_number: Mapped[int] = mapped_column(Integer, nullable=False)
    step_type: Mapped[str] = mapped_column(String(20), default="EMAIL", nullable=False)  # EMAIL, WAIT
    delay_days: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    subject: Mapped[str | None] = mapped_column(Text, nullable=True)
    body: Mapped[str | None] = mapped_column(Text, nullable=True)

    campaign: Mapped["Campaign"] = relationship("Campaign", back_populates="steps")

    __table_args__ = (
        UniqueConstraint("campaign_id", "step_number", name="uq_campaign_step_number"),
    )
