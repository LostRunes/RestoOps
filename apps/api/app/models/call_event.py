from typing import TYPE_CHECKING
from sqlalchemy import ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base import Base, TimestampMixin, UUIDMixin

if TYPE_CHECKING:
    from app.models.call import Call


class CallEvent(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "call_events"

    call_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("calls.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )

    # INITIATED, RINGING, ANSWERED, ENDED, FAILED, RECORDING_AVAILABLE, STATUS_UPDATE
    event_type: Mapped[str] = mapped_column(String(50), nullable=False)

    payload: Mapped[dict | None] = mapped_column(JSONB, nullable=True)

    # SYSTEM, EXOTEL_WEBHOOK, WEBRTC_SIGNAL
    source: Mapped[str] = mapped_column(String(20), nullable=False, default="SYSTEM")

    # Relationships
    call: Mapped["Call"] = relationship("Call", back_populates="events")
