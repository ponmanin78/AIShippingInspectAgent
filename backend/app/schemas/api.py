from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

from app.models.domain import JobStatus, ReviewAction


class PolicyRead(BaseModel):
    id: str
    name: str
    category: str
    region: str
    description: str

    model_config = ConfigDict(from_attributes=True)


class AuditLogRead(BaseModel):
    job_id: str
    action: str
    details: dict[str, Any] | None = None
    timestamp: datetime

    model_config = ConfigDict(from_attributes=True)


class JobRead(BaseModel):
    id: str
    status: JobStatus
    fleet_type: str | None = None
    region: str
    file_name: str | None = None
    policies_used: list[dict[str, Any]] | None = None
    validation_result: dict[str, Any] | None = None
    report: dict[str, Any] | None = None
    error: str | None = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class SubmitResponse(BaseModel):
    job_id: str
    status: JobStatus


class ReviewRequest(BaseModel):
    action: ReviewAction
    comments: str | None = Field(default=None, max_length=2000)


class ReviewResponse(BaseModel):
    job: JobRead
    notification: dict[str, Any]


class FailureReason(BaseModel):
    reason: str
    count: int


class MetricsResponse(BaseModel):
    total_requests: int
    approved: int
    rejected: int
    failed: int
    pending_reviews: int
    pass_count: int
    fail_count: int
    failure_reasons: list[FailureReason]


class AgentClassification(BaseModel):
    fleet_type: Literal["Commercial", "Passenger"]
    confidence: float = Field(ge=0, le=1)
    reason: str


class AgentValidation(BaseModel):
    passed: bool
    reasons: list[str]
    missing_documents: list[str]
    policy_results: list[dict[str, Any]]


class AgentReport(BaseModel):
    title: str
    summary: str
    recommendation: Literal["APPROVE", "REJECT", "REQUEST_MORE_INFO"]
    details: dict[str, Any]

