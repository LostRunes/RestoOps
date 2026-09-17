from sqlalchemy import ForeignKey, String, Text, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base import Base, TimestampMixin, UUIDMixin


class Message(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "messages"

    conversation_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("conversations.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )

    direction: Mapped[str] = mapped_column(String(10), nullable=False)  # INBOUND, OUTBOUND
    sender: Mapped[str] = mapped_column(String(255), nullable=False)
    recipient: Mapped[str] = mapped_column(String(255), nullable=False)

    subject: Mapped[str | None] = mapped_column(String(500), nullable=True)
    body: Mapped[str] = mapped_column(Text, nullable=False)

    message_id: Mapped[str | None] = mapped_column(String(500), nullable=True, index=True)
    in_reply_to: Mapped[str | None] = mapped_column(String(500), nullable=True)
    references: Mapped[str | None] = mapped_column(Text, nullable=True)

    status: Mapped[str] = mapped_column(String(20), default="SENT", nullable=False)  # SENT, DELIVERED, FAILED, RECEIVED
    activity_metadata: Mapped[dict | None] = mapped_column("metadata", JSON, nullable=True)

    conversation: Mapped["Conversation"] = relationship("Conversation", back_populates="messages")
