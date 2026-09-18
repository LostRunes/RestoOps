from datetime import datetime
from typing import Any
from pydantic import BaseModel


class NotificationResponse(BaseModel):
    id: str
    organization_id: str
    user_id: str
    type: str
    title: str
    body: str
    entity_type: str | None
    entity_id: str | None
    priority: str
    is_read: bool
    read_at: datetime | None
    notification_metadata: dict | None
    created_at: datetime

    model_config = {"from_attributes": True}


class NotificationListResponse(BaseModel):
    notifications: list[NotificationResponse]
    total: int
    unread_count: int
    page: int
    page_size: int


class UnreadCountResponse(BaseModel):
    count: int
