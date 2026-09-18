from sqlalchemy import Boolean, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base import Base, TimestampMixin, UUIDMixin

from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from app.models.lead_contact import LeadContact
    from app.models.lead_verification import LeadVerification
    from app.models.campaign_lead import CampaignLead
    from app.models.lead_activity import LeadActivity



class Lead(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "leads"

    organization_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )
    restaurant_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("restaurants.id", ondelete="SET NULL"),
        nullable=True, index=True,
    )

    company_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    contact_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    email: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)
    phone: Mapped[str | None] = mapped_column(String(50), nullable=True)
    address: Mapped[str | None] = mapped_column(Text, nullable=True)
    industry: Mapped[str | None] = mapped_column(String(100), nullable=True)
    company_size: Mapped[str | None] = mapped_column(String(50), nullable=True)

    # Source: CSV | MANUAL | PUBLIC | API
    source: Mapped[str] = mapped_column(String(50), default="MANUAL", nullable=False)

    # Score 0-100 derived from verification + pipeline state
    score: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    # Priority: HOT | HIGH | MEDIUM | LOW
    priority: Mapped[str] = mapped_column(String(20), default="MEDIUM", nullable=False)

    # Pipeline: NEW → VERIFIED → CONTACTED → INTERESTED → QUALIFIED → QUOTE_SENT → NEGOTIATING → WON → LOST
    pipeline_status: Mapped[str] = mapped_column(
        String(30), default="NEW", nullable=False, index=True
    )

    contacts: Mapped[list["LeadContact"]] = relationship(
        "LeadContact", back_populates="lead", cascade="all, delete-orphan"
    )
    activities: Mapped[list["LeadActivity"]] = relationship(
        "LeadActivity", back_populates="lead", cascade="all, delete-orphan"
    )
    verifications: Mapped[list["LeadVerification"]] = relationship(
        "LeadVerification", back_populates="lead", cascade="all, delete-orphan"
    )
