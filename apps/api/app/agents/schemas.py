"""
Pydantic schemas for structured agent outputs.
"""
from __future__ import annotations
from typing import List, Optional
from pydantic import BaseModel, Field


class SuggestedAction(BaseModel):
    tool: str                          # create_quote, send_email, update_lead, schedule_followup, create_task, add_suppression
    description: str                   # Human-readable description for the approval UI
    arguments: dict = Field(default_factory=dict)
    confidence: float = Field(ge=0.0, le=1.0)
    requires_approval: bool = True


class ConversationAnalysis(BaseModel):
    intent: str                        # NEEDS_QUOTE | INTERESTED | NOT_INTERESTED | QUESTION | COMPLAINT | SCHEDULING | GENERAL
    sentiment: str                     # POSITIVE | NEUTRAL | NEGATIVE
    urgency: str                       # HIGH | MEDIUM | LOW

    guest_count: Optional[int] = None
    event_date: Optional[str] = None
    event_type: Optional[str] = None
    budget_mentioned: Optional[str] = None
    dietary_requirements: Optional[List[str]] = None

    key_points: List[str] = Field(default_factory=list)

    suggested_lead_status: Optional[str] = None   # INTERESTED | QUALIFIED | WON | LOST

    suggested_actions: List[SuggestedAction] = Field(default_factory=list)
