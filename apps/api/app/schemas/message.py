from datetime import datetime
from pydantic import BaseModel, ConfigDict


class MessageCreate(BaseModel):
    body: str
    subject: str | None = None


class MessageResponse(BaseModel):
    id: str
    conversation_id: str
    direction: str  # INBOUND, OUTBOUND
    sender: str
    recipient: str
    subject: str | None = None
    body: str
    message_id: str | None = None
    in_reply_to: str | None = None
    references: str | None = None
    status: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
