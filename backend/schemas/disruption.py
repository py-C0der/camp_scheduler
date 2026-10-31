"""
Pydantic Schemas for Module 5: Disruption Reporting and Impact Analysis.
Supports all 5 official disruption types:
1. faculty_unavailable
2. room_unavailable
3. add_faculty
4. add_session
5. remove_session
"""

from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field


class DisruptionChange(BaseModel):
    type: str = Field(..., description="Change type: faculty_unavailable, room_unavailable, add_faculty, add_session, remove_session")
    faculty_id: Optional[str] = None
    room_id: Optional[str] = None
    days: Optional[List[str]] = None
    periods: Optional[List[int]] = None
    reason: Optional[str] = None
    faculty: Optional[Dict[str, Any]] = None
    session: Optional[Dict[str, Any]] = None
    session_id: Optional[str] = None


class DisruptionCreateRequest(BaseModel):
    id: Optional[str] = Field(None, description="Unique disruption ID (e.g. DIS-2027-01)")
    title: Optional[str] = Field(None, description="Human-readable summary title")
    description: str = Field(..., description="Detailed description of campus disruption")
    dataset_id: Optional[str] = Field("cit-public-v1", description="Associated dataset ID")
    changes: List[Dict[str, Any]] = Field(..., description="List of official disruption changes")


class DisruptionResponse(BaseModel):
    id: str
    title: Optional[str] = None
    description: str
    dataset_id: str
    changes: List[Dict[str, Any]]
    status: str
    reported_by: str
    reported_at: str
    sessions_moved: int = 0
    impact_summary: Optional[Dict[str, Any]] = None


class AffectedSessionDetail(BaseModel):
    session_id: str
    course_id: str
    faculty_id: str
    groups: List[str]
    current_day: str
    current_start_period: int
    current_room_id: str
    conflict_type: str  # faculty_unavailable, room_unavailable, removed_session
    conflict_detail: str


class DisruptionImpactResponse(BaseModel):
    disruption_id: str
    is_impacted: bool
    total_affected_sessions: int
    directly_affected_sessions: List[AffectedSessionDetail]
    affected_faculty: List[Dict[str, Any]]
    affected_rooms: List[Dict[str, Any]]
    affected_student_groups: List[str]
    new_sessions_to_schedule: List[Dict[str, Any]]
    removed_sessions: List[str]
    exam_conflicts: List[Dict[str, Any]] = []
    booking_conflicts: List[Dict[str, Any]] = []
    summary_text: str


class DisruptionDashboardSummary(BaseModel):
    total_disruptions: int
    open_disruptions: int
    analyzing_disruptions: int
    proposals_awaiting_approval: int
    approved_reschedulings: int
    unresolved_disruptions: int
    latest_disruption_id: Optional[str] = None
    active_timetable_version: str = "baseline"
