"""
Pydantic Schemas for Module 5: Rescheduling Proposals, Comparisons, and Timetable Versioning.
"""

from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field


class RescheduleGenerateRequest(BaseModel):
    time_limit_seconds: Optional[int] = Field(45, ge=5, le=180, description="CP-SAT solver timeout in seconds")
    target_version_name: Optional[str] = Field(None, description="Optional custom version name for proposed timetable")


class ProposalAssignmentItem(BaseModel):
    session_id: str
    course_id: Optional[str] = None
    faculty_id: Optional[str] = None
    groups: List[str] = []
    original_day: Optional[str] = None
    original_start_period: Optional[int] = None
    original_room_id: Optional[str] = None
    proposed_day: str
    proposed_start_period: int
    proposed_room_id: str
    is_moved: bool
    change_type: str  # unchanged, time_and_room, time_only, room_only, new_session, removed_session
    change_reason: Optional[str] = None


class ReschedulingProposalResponse(BaseModel):
    id: str
    disruption_id: str
    baseline_timetable_id: str
    target_timetable_version: str
    status: str  # proposed, approved, rejected
    solver_status: str  # OPTIMAL, FEASIBLE, INFEASIBLE
    solve_time_seconds: float
    sessions_moved: int
    time_changed: int
    room_only_changed: int
    unchanged_sessions: int
    hard_violations_count: int
    hard_violations: List[Dict[str, Any]] = []
    soft_penalty: int
    created_by: str
    created_at: str
    decided_by: Optional[str] = None
    decided_at: Optional[str] = None
    decision_reason: Optional[str] = None


class ProposalComparisonResponse(BaseModel):
    proposal_id: str
    disruption_id: str
    baseline_version: str
    proposed_version: str
    summary: Dict[str, Any]
    validation: Dict[str, Any]
    changed_sessions: List[ProposalAssignmentItem]
    all_assignments: Optional[List[ProposalAssignmentItem]] = None


class ProposalDecisionRequest(BaseModel):
    reason: Optional[str] = Field("Approved after review and constraint validation", description="Mandatory reason/note for audit log")


class TimetableVersionItem(BaseModel):
    id: str
    name: str
    is_active: bool
    source: str
    created_at: str
    sessions_count: int = 0
    sessions_moved_from_baseline: int = 0
