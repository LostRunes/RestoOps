from datetime import datetime
from pydantic import BaseModel, ConfigDict
from app.schemas.message import MessageResponse


class ConversationResponse(BaseModel):
    id: str
    organization_id: str
    restaurant_id: str | None = None
    lead_id: str
    channel: str
    status: str
    subject: str | None = None
    message_count: int
    last_message_at: datetime | None = None
    created_at: datetime
    updated_at: datetime
    lead_email: str | None = None
    lead_contact_name: str | None = None

    model_config = ConfigDict(from_attributes=True)


class ConversationDetailResponse(ConversationResponse):
    messages: list[MessageResponse] = []
