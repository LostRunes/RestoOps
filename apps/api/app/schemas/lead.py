from __future__ import annotations
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, EmailStr


# ─── Lead Contact ─────────────────────────────────────────────────────────────

class LeadContactCreate(BaseModel):
    name: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    role: Optional[str] = None
    is_primary: bool = False


class LeadContactResponse(LeadContactCreate):
    id: str
    lead_id: str

    model_config = {"from_attributes": True}


# ─── Lead ─────────────────────────────────────────────────────────────────────

class LeadCreate(BaseModel):
    company_name: Optional[str] = None
    contact_name: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    address: Optional[str] = None
    industry: Optional[str] = None
    company_size: Optional[str] = None
    source: str = "MANUAL"
    priority: str = "MEDIUM"
    pipeline_status: str = "NEW"
    restaurant_id: Optional[str] = None
    contacts: list[LeadContactCreate] = []


class LeadUpdate(BaseModel):
    company_name: Optional[str] = None
    contact_name: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    address: Optional[str] = None
    industry: Optional[str] = None
    company_size: Optional[str] = None
    priority: Optional[str] = None
    pipeline_status: Optional[str] = None
    restaurant_id: Optional[str] = None


class LeadResponse(BaseModel):
    id: str
    organization_id: str
    company_name: Optional[str]
    contact_name: Optional[str]
    email: Optional[str]
    phone: Optional[str]
    address: Optional[str]
    industry: Optional[str]
    company_size: Optional[str]
    source: str
    score: int
    priority: str
    pipeline_status: str
    restaurant_id: Optional[str]
    created_at: datetime
    updated_at: datetime
    contacts: list[LeadContactResponse] = []

    model_config = {"from_attributes": True}


class LeadListResponse(BaseModel):
    items: list[LeadResponse]
    total: int
    page: int
    size: int


# ─── CSV Import ───────────────────────────────────────────────────────────────

class CSVImportResponse(BaseModel):
    job_id: str
    total_rows: int
    message: str
