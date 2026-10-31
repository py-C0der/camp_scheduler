"""
Event Definitions for Notification System.
"""

from typing import Dict, Any, Optional
from pydantic import BaseModel, Field
import time
import uuid


class EventTypes:
    # Module 2 Timetable Events
    TIMETABLE_APPROVED = "TIMETABLE_APPROVED"
    TIMETABLE_UPDATED = "TIMETABLE_UPDATED"
    SESSION_RESCHEDULED = "SESSION_RESCHEDULED"

    # Module 3 Examination Events
    EXAM_SCHEDULE_APPROVED = "EXAM_SCHEDULE_APPROVED"
    EXAM_SCHEDULE_UPDATED = "EXAM_SCHEDULE_UPDATED"

    # Module 4 Venue Booking Events
    BOOKING_SUBMITTED = "BOOKING_SUBMITTED"
    BOOKING_APPROVED = "BOOKING_APPROVED"
    BOOKING_REJECTED = "BOOKING_REJECTED"
    BOOKING_ALTERNATIVE_OFFERED = "BOOKING_ALTERNATIVE_OFFERED"
    BOOKING_CANCELLED = "BOOKING_CANCELLED"

    # Module 5 Disruption & Rescheduling Events
    DISRUPTION_REPORTED = "DISRUPTION_REPORTED"
    RESCHEDULING_PROPOSED = "RESCHEDULING_PROPOSED"
    RESCHEDULING_APPROVED = "RESCHEDULING_APPROVED"
    RESCHEDULING_REJECTED = "RESCHEDULING_REJECTED"

    # Approval Events
    APPROVAL_REQUIRED = "APPROVAL_REQUIRED"
    APPROVAL_COMPLETED = "APPROVAL_COMPLETED"


class NotificationEvent(BaseModel):
    id: str = Field(default_factory=lambda: f"evt_{uuid.uuid4().hex[:12]}")
    event_type: str
    category: str # 'timetable', 'examination', 'venue_booking', 'disruption', 'approval'
    severity: str # 'critical', 'high', 'medium', 'low'
    related_module: str # 'module_1' .. 'module_5'
    related_record_id: Optional[str] = None
    published_by: str = "system"
    timestamp: float = Field(default_factory=time.time)
    payload: Dict[str, Any] = Field(default_factory=dict)
