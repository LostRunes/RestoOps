from sqlalchemy import ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column
from app.db.base import Base, TimestampMixin, UUIDMixin


class SuppressionEntry(Base, UUIDMixin, TimestampMixin):
    """
    Global per-organization suppression list.
    Any email/phone on this list must not be contacted.
    Populated from: bounces, unsubscribes, manual blocks, AI suggestions.
    """
    __tablename__ = "suppression_list"
    __table_args__ = (
        UniqueConstraint("organization_id", "email", name="uq_suppression_org_email"),
    )

    organization_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )
    email: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)
    phone: Mapped[str | None] = mapped_column(String(50), nullable=True)

    # UNSUBSCRIBED | BOUNCED | DO_NOT_CONTACT | MANUAL_BLOCK | INVALID_EMAIL
    reason: Mapped[str] = mapped_column(String(50), nullable=False)

    # SYSTEM | MANUAL | AI
    source: Mapped[str] = mapped_column(String(50), default="SYSTEM", nullable=False)
