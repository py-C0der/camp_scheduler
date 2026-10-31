"""
Pydantic Schemas for Module 4: Venue Booking Requests and Extraction.
"""

from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field


class BookingWindow(BaseModel):
    day: str
    from_period: int
    to_period: int


class BookingParseRequest(BaseModel):
    text: str = Field(..., description="Plain English or Hinglish text booking request")
    user_role: Optional[str] = Field("club", description="User role submitting the request")
    department: Optional[str] = Field(None, description="Department if coordinator or faculty")


class BookingDraftResponse(BaseModel):
    id: str
    raw_text: str
    extracted: Dict[str, Any]
    is_complete: bool
    missing_fields: List[str]
    clarification_questions: List[str]
    contradictions: List[str]


class BookingCreateRequest(BaseModel):
    title: str
    requested_category: str
    attendance: int
    duration_periods: int
    room_types: List[str]
    windows: List[BookingWindow]
    needs: Optional[List[str]] = []
    mandatory_for_groups: Optional[List[str]] = []
    requested_room: Optional[str] = None
    series_id: Optional[str] = None
    raw_text: Optional[str] = None
    department: Optional[str] = None


class BookingUpdateRequest(BaseModel):
    title: Optional[str] = None
    requested_category: Optional[str] = None
    attendance: Optional[int] = None
    duration_periods: Optional[int] = None
    room_types: Optional[List[str]] = None
    windows: Optional[List[BookingWindow]] = None
    needs: Optional[List[str]] = None
    mandatory_for_groups: Optional[List[str]] = None
    requested_room: Optional[str] = None
    series_id: Optional[str] = None
    department: Optional[str] = None


class BookingRecordResponse(BaseModel):
    id: str
    title: Optional[str] = None
    requester: Optional[str] = None
    role: str
    department: Optional[str] = None
    requested_category: str
    effective_category: str
    attendance: int
    duration_periods: int
    room_types: List[str]
    windows: List[BookingWindow]
    needs: List[str]
    mandatory_for_groups: List[str]
    requested_room: Optional[str] = None
    series_id: Optional[str] = None
    raw_text: Optional[str] = None
    submitted_at: str
    created_by: Optional[str] = None
    status: str  # pending, approved, rejected, alternative_offered, cancelled
    assigned_room_id: Optional[str] = None
    assigned_day: Optional[str] = None
    assigned_start_period: Optional[int] = None
    assigned_end_period: Optional[int] = None
    decision_reason: Optional[str] = None
    decision_by: Optional[str] = None
    decision_at: Optional[str] = None
    is_cancelled: bool = False
    cancelled_at: Optional[str] = None
    cancelled_by: Optional[str] = None
    cancellation_note: Optional[str] = None


class BookingSummaryResponse(BaseModel):
    total_requests: int
    pending_requests: int
    approved_requests: int
    rejected_requests: int
    alternative_offers: int
    cancelled_requests: int
    booking_score: float
    max_possible_score: float
    priority_inversions: List[str]
    last_updated: Optional[str] = None
