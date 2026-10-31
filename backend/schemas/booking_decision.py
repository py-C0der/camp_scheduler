"""
Pydantic Schemas for Module 4: Booking Decisions, Alternatives, and Priority Configurations.
"""

from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field


class BookingDecisionRequest(BaseModel):
    decision: str = Field(..., description="Decision: approved, rejected, or alternative_offered")
    room_id: Optional[str] = None
    day: Optional[str] = None
    start_period: Optional[int] = None
    end_period: Optional[int] = None
    reason: Optional[str] = None


class BookingApproveRequest(BaseModel):
    room_id: Optional[str] = None
    day: Optional[str] = None
    start_period: Optional[int] = None
    reason: Optional[str] = "Approved after eligibility checks"


class BookingRejectRequest(BaseModel):
    reason: str = Field(..., description="Mandatory detailed explanation for rejection")


class BookingAlternativeOffer(BaseModel):
    id: Optional[int] = None
    booking_id: str
    room_id: str
    day: str
    start_period: int
    end_period: int
    capacity: int
    features: List[str] = []
    reason: str
    status: str = "offered"


class BookingAcceptAlternativeRequest(BaseModel):
    alternative_id: Optional[int] = None
    room_id: Optional[str] = None
    day: Optional[str] = None
    start_period: Optional[int] = None


class BookingCancellationRequest(BaseModel):
    reason: Optional[str] = Field("Cancelled by user", description="Reason for cancellation")


class PriorityConfigResponse(BaseModel):
    priority_order: List[str]
    role_category_cap: Dict[str, str]
    version: int
    updated_by: str
    updated_at: str


class PriorityConfigUpdate(BaseModel):
    priority_order: List[str]
    role_category_cap: Optional[Dict[str, str]] = None


class ConflictItem(BaseModel):
    conflict_type: str
    entity_id: str
    day: str
    period: int
    description: str


class BookingValidationResult(BaseModel):
    booking_id: str
    is_valid: bool
    status_candidate: str  # approved, alternative_needed, rejected
    violations: List[str]
    conflicts: List[ConflictItem]
    effective_category: str
    capacity_check: Dict[str, Any]
    feature_check: Dict[str, Any]
    details: str
