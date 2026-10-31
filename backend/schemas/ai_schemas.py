"""
Pydantic Schemas for Module 8: CIT AI Scheduling Assistant & Decision Explainability.
Defines strict data models for chat conversations, request extraction, clarification,
schedule-change proposals, decision evidence, and explanations.
"""

from typing import Dict, Any, List, Optional, Union
from pydantic import BaseModel, Field


class AIChatMessage(BaseModel):
    role: str = Field(..., description="'user', 'assistant', or 'system'")
    content: str = Field(..., description="Message text content")
    timestamp: Optional[str] = None


class AIChatRequest(BaseModel):
    message: str = Field(..., min_length=1, description="Natural language input from user in English or Hinglish")
    conversation_id: Optional[str] = Field(None, description="Optional ID of existing conversation to continue context")
    context: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Active user profile, page context, target filters")


class AIScheduleChangeRequest(BaseModel):
    request_type: str = Field("reschedule_session", description="reschedule_session | faculty_unavailable | room_change | swap")
    faculty_id: Optional[str] = Field(None, description="Authenticated faculty member ID")
    session_id: Optional[str] = Field(None, description="Target session ID e.g. CS101-L1")
    course_id: Optional[str] = Field(None, description="Course ID e.g. CS101")
    current_day: Optional[str] = Field(None, description="Current scheduled day (MON-FRI)")
    current_period: Optional[int] = Field(None, description="Current scheduled starting period (1-9)")
    requested_day: Optional[str] = Field(None, description="Desired destination day (MON-FRI)")
    requested_period: Optional[int] = Field(None, description="Desired destination starting period (1-9)")
    preferred_time_range: Optional[str] = Field(None, description="morning | afternoon | earlier | later")
    requested_room: Optional[str] = Field(None, description="Optional specific requested room ID")
    reason: Optional[str] = Field("Faculty schedule change request", description="Reason for request")
    unavailability_periods: Optional[List[int]] = Field(default_factory=list, description="Periods marked unavailable if applicable")
    additional_conditions: Optional[Dict[str, Any]] = Field(default_factory=dict)
    requires_clarification: bool = Field(False, description="Whether request is ambiguous or missing required fields")
    missing_fields: List[str] = Field(default_factory=list, description="List of missing information keys")


class AIClarifyRequest(BaseModel):
    conversation_id: str = Field(..., description="Active conversation ID")
    clarification_answer: str = Field(..., description="User response to clarification prompt")
    draft_request: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Current draft request state")


class AIExplanationRequest(BaseModel):
    question: str = Field(..., description="Natural language question about a scheduling or booking decision")
    question_type: Optional[str] = Field(
        None,
        description="timetable_slot | room_selection | booking_rejection | reschedule_infeasible | general"
    )
    target_id: Optional[str] = Field(None, description="Session ID, Booking ID, or Room ID if known")
    day: Optional[str] = Field(None, description="MON | TUE | WED | THU | FRI")
    period: Optional[int] = Field(None, description="1-9")


class AIExplanationResponse(BaseModel):
    question: str
    question_type: str
    target_id: Optional[str] = None
    explanation: str = Field(..., description="Human-readable explanation grounded strictly in backend evidence")
    evidence: Dict[str, Any] = Field(default_factory=dict, description="Concrete database and solver records supporting explanation")
    rules_involved: List[str] = Field(default_factory=list, description="Constraint codes e.g. H2, H3, H9, H12, H14")
    alternatives: List[Dict[str, Any]] = Field(default_factory=list, description="Feasible alternatives if available")
    is_counterfactual: bool = Field(False, description="Whether inquiry tested an unfeasible placement")


class AIChatResponse(BaseModel):
    message: str = Field(..., description="Assistant response text")
    conversation_id: str = Field(..., description="Conversation identifier")
    intent: str = Field(..., description="Detected intent: schedule_change | explain | unavailability | security_block | general")
    extracted_request: Optional[AIScheduleChangeRequest] = None
    requires_clarification: bool = False
    clarification_questions: List[str] = Field(default_factory=list)
    proposal: Optional[Dict[str, Any]] = Field(None, description="Generated rescheduling proposal if feasible")
    explanation: Optional[AIExplanationResponse] = None
    validation_status: Optional[str] = Field(None, description="PASS | FAILED | NOT_APPLICABLE")
    validation_errors: List[str] = Field(default_factory=list)
    suggested_prompts: List[str] = Field(default_factory=list)
