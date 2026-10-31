from __future__ import annotations

from typing import Any
from pydantic import BaseModel, Field


class ExamRoomDetail(BaseModel):
    room_id: str
    name: str
    building: str
    type: str
    normal_capacity: int
    effective_exam_seats: int


class ExamRecord(BaseModel):
    exam_id: str
    course_ids: list[str]
    groups: list[str]
    size: int
    duration_hours: int = 2
    day: str | None = None
    session: str | None = None  # AM or PM
    rooms: list[str] = Field(default_factory=list)
    total_effective_seats: int = 0
    is_multi_room: bool = False
    status: str = "scheduled"  # scheduled | unscheduled


class ExamDetailResponse(BaseModel):
    exam_id: str
    course_ids: list[str]
    groups: list[str]
    size: int
    duration_hours: int
    day: str | None
    session: str | None
    rooms: list[str]
    total_effective_seats: int
    is_multi_room: bool
    surplus_seats: int = 0
    breakdown: list[ExamRoomDetail] = Field(default_factory=list)
    validation_status: str = "VALID"


class ExamListResponse(BaseModel):
    total: int
    page: int
    limit: int
    items: list[ExamRecord]


class ExamSummaryResponse(BaseModel):
    total_exams: int
    scheduled_exams: int
    unscheduled_exams: int
    total_allocated_rooms: int
    multi_room_exams: int
    pending_approval: bool
    validation_status: str
    exam_soft_penalty: int
    latest_schedule_version: str | None = None
    exam_days: list[str] = Field(default_factory=list)
    exam_sessions: list[dict[str, Any]] = Field(default_factory=list)


class ExamGenerateRequest(BaseModel):
    time_limit_seconds: float = Field(default=20.0, ge=2.0, le=120.0)
    num_workers: int = Field(default=4, ge=1, le=16)


class ExamApprovalRequest(BaseModel):
    approved_by: str = "admin"
    note: str | None = None


class ExamValidationResponse(BaseModel):
    valid: bool
    hard_violation_count: int
    hard_violations: list[dict[str, Any]]
    exam_soft_penalty: int
    diagnostics: dict[str, Any] | None = None
