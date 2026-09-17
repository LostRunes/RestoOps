from datetime import datetime
from pydantic import BaseModel, ConfigDict


class CampaignStepCreate(BaseModel):
    step_number: int = 1
    step_type: str = "EMAIL"  # EMAIL, WAIT
    delay_days: int = 0
    subject: str | None = None
    body: str | None = None


class CampaignStepResponse(CampaignStepCreate):
    id: str
    campaign_id: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class CampaignCreate(BaseModel):
    name: str
    description: str | None = None
    restaurant_id: str | None = None
    target_filters: dict | None = None
    steps: list[CampaignStepCreate] = []


class CampaignUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    target_filters: dict | None = None
    status: str | None = None


class CampaignResponse(BaseModel):
    id: str
    organization_id: str
    restaurant_id: str | None = None
    name: str
    description: str | None = None
    status: str
    target_filters: dict | None = None
    created_by: str | None = None
    started_at: datetime | None = None
    completed_at: datetime | None = None
    created_at: datetime
    updated_at: datetime
    steps: list[CampaignStepResponse] = []

    model_config = ConfigDict(from_attributes=True)


class CampaignLeadResponse(BaseModel):
    id: str
    campaign_id: str
    lead_id: str
    current_step: int
    status: str
    next_step_at: datetime | None = None
    created_at: datetime
    lead_email: str | None = None
    lead_contact_name: str | None = None

    model_config = ConfigDict(from_attributes=True)


class CampaignAnalyticsResponse(BaseModel):
    total_leads: int
    pending: int
    in_progress: int
    completed: int
    replied: int
    bounced: int
    unsubscribed: int
    skipped: int
