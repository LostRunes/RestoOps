from datetime import datetime
from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base import Base, UUIDMixin


class LeadVerification(Base, UUIDMixin):
    """
    Stores full BounceBlitz-style verification result for a single email address.
    Each lead can have multiple verification attempts (latest is authoritative).
    """
    __tablename__ = "lead_verifications"

    lead_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("leads.id", ondelete="CASCADE"),
        nullable=True, index=True,
    )
    organization_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )

    email: Mapped[str] = mapped_column(String(255), nullable=False, index=True)

    # BounceBlitz 9-status system:
    # safe | role | catch_all | disposable | inbox_full | spamtrap | disabled | invalid | unknown
    status: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    status_label: Mapped[str | None] = mapped_column(String(50), nullable=True)
    score: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    reason: Mapped[str | None] = mapped_column(String(100), nullable=True)

    # Granular checks
    syntax_valid: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    domain_valid: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    mx_valid: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    disposable: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    role_based: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    catch_all: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    spamtrap: Mapped[bool | None] = mapped_column(Boolean, nullable=True)

    # SMTP details
    smtp_code: Mapped[int | None] = mapped_column(Integer, nullable=True)
    smtp_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    mx_host: Mapped[str | None] = mapped_column(String(255), nullable=True)
    provider: Mapped[str | None] = mapped_column(String(50), nullable=True)

    # Performance
    latency_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    attempts: Mapped[int] = mapped_column(Integer, default=1, nullable=False)

    checked_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    lead: Mapped["Lead | None"] = relationship("Lead", back_populates="verifications")
