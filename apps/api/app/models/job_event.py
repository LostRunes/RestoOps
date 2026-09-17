from sqlalchemy import ForeignKey, String
from sqlalchemy import JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base import Base, TimestampMixin, UUIDMixin


class JobEvent(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "job_events"

    job_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("jobs.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )

    # STARTED | PROGRESS | COMPLETED | FAILED | CANCELLED | ITEM_PROCESSED
    event_type: Mapped[str] = mapped_column(String(50), nullable=False)
    payload: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    job: Mapped["Job"] = relationship("Job", back_populates="events")
