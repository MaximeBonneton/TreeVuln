"""Schemas des événements de notification ENISA (Phase 3 CRA)."""
from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class MilestoneState(BaseModel):
    due_at: datetime | None = None
    remaining_seconds: int | None = None
    overdue: bool = False
    submitted_at: datetime | None = None


class EnisaEventSummary(BaseModel):
    id: int
    tree_id: int
    cve_id: str
    status: str
    detected_at: datetime
    last_detected_at: datetime
    confirmed_at: datetime | None
    redetection_count: int
    milestones: dict[str, MilestoneState] = Field(default_factory=dict)

    model_config = {"from_attributes": True}


class EnisaEventDetail(EnisaEventSummary):
    corrective_available_at: datetime | None
    affected_assets: list[Any]
    evaluation_context: dict[str, Any]
    drafts: dict[str, Any]
    confirmed_by: str | None
    dismissed_by: str | None
    dismiss_reason: str | None
    close_reason: str | None


class EnisaEventListResponse(BaseModel):
    events: list[EnisaEventSummary]
    total: int


class DismissRequest(BaseModel):
    reason: str = Field(min_length=1)


class CloseRequest(BaseModel):
    reason: str | None = None


class DraftUpdateRequest(BaseModel):
    fields: dict[str, Any]


class CorrectiveDateRequest(BaseModel):
    corrective_available_at: datetime


class EnisaSummaryResponse(BaseModel):
    candidates: int
    confirmed: int
    overdue_milestones: int
