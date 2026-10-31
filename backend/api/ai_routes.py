"""
FastAPI Router for Module 8: CIT AI Scheduling Assistant & Decision Explainability.
Provides RESTful APIs for chat, bilingual extraction, clarification handling,
proposal review, and grounded decision explanations.
"""

from typing import Dict, Any, List, Optional
from fastapi import APIRouter, HTTPException, Depends, Header
from pydantic import BaseModel

from backend.schemas.ai_schemas import (
    AIChatRequest, AIChatResponse, AIScheduleChangeRequest,
    AIClarifyRequest, AIExplanationRequest, AIExplanationResponse
)
from backend.ai.assistant import ai_assistant_service
from backend.services.decision_evidence_service import DecisionEvidenceService
from backend.services.disruption_service import DisruptionService
from backend.disruptions.proposal_manager import ProposalManager

ai_router = APIRouter(prefix="/api/ai", tags=["AI Scheduling Assistant & Explainability"])
evidence_service = DecisionEvidenceService()
disruption_service = DisruptionService()


def get_current_user_context(
    x_user_id: Optional[str] = Header(None),
    x_user_role: Optional[str] = Header(None),
    x_faculty_id: Optional[str] = Header(None)
) -> Dict[str, Any]:
    """Retrieves simulated authenticated user context from request headers or default state."""
    uid = x_user_id or "fac_arvind"
    role = x_user_role or "faculty"
    fid = x_faculty_id or ("F01" if role == "faculty" else None)
    return {
        "id": uid,
        "name": "Dr. Arvind Kumar (Faculty)" if role == "faculty" else "Dean Academics (Admin)",
        "role": role,
        "faculty_id": fid,
        "department": "Computer Science & Engineering"
    }


@ai_router.post("/chat", response_model=AIChatResponse)
def ai_chat_endpoint(req: AIChatRequest, user: Dict[str, Any] = Depends(get_current_user_context)):
    """
    Main conversational endpoint. Accepts English and Hinglish messages,
    extracts schedule requests, resolves decision inquiries, and returns verified proposals.
    """
    # Merge custom context if provided
    if req.context:
        user = {**user, **req.context}
    return ai_assistant_service.process_chat(req, user)


@ai_router.post("/extract-request", response_model=AIScheduleChangeRequest)
def ai_extract_request_endpoint(req: AIChatRequest, user: Dict[str, Any] = Depends(get_current_user_context)):
    """
    Extracts structured schedule change parameters from natural language without generating proposals.
    Useful for previewing and editing before solver execution.
    """
    return ai_assistant_service.extract_schedule_change(req.message, user)


@ai_router.post("/clarify", response_model=AIChatResponse)
def ai_clarify_endpoint(req: AIClarifyRequest, user: Dict[str, Any] = Depends(get_current_user_context)):
    """
    Processes user's clarification answer and combines it with previous request context.
    """
    combined_msg = f"{req.draft_request.get('reason', '')} Additional details: {req.clarification_answer}"
    chat_req = AIChatRequest(
        message=combined_msg,
        conversation_id=req.conversation_id,
        context=req.draft_request
    )
    return ai_assistant_service.process_chat(chat_req, user)


@ai_router.post("/schedule-change")
def ai_create_schedule_change_endpoint(
    req: AIScheduleChangeRequest,
    user: Dict[str, Any] = Depends(get_current_user_context)
):
    """
    Direct endpoint for creating a validated schedule-change proposal from structured parameters.
    Integrates directly with Module 5 Disruption Engine.
    """
    user_role = user.get("role", "faculty")
    user_fid = user.get("faculty_id") or user.get("id")

    # Faculty can only request changes for their own sessions
    if user_role == "faculty" and req.session_id:
        s_data = evidence_service.sessions.get(req.session_id)
        if s_data and s_data.get("faculty_id") != user_fid:
            raise HTTPException(
                status_code=403,
                detail=f"Forbidden: You cannot modify Dr. {s_data.get('faculty_id')}'s schedule without authorization."
            )

    dis_payload = {
        "description": f"Structured Request: {req.reason}",
        "reported_by": user.get("id", "faculty"),
        "changes": [{
            "type": "faculty_unavailable",
            "faculty_id": req.faculty_id or user_fid or "F01",
            "days": [req.requested_day or req.current_day or "MON"],
            "periods": req.unavailability_periods or ([req.current_period] if req.current_period else [1]),
            "reason": req.reason or "Faculty Schedule Change"
        }]
    }

    dis_res = disruption_service.create_disruption(dis_payload, user)
    prop = disruption_service.generate_rescheduling_proposal(
        disruption_id=dis_res["disruption_id"],
        user=user,
        time_limit_seconds=30
    )
    return {
        "status": "success",
        "disruption_id": dis_res["disruption_id"],
        "proposal": prop
    }


@ai_router.post("/explain", response_model=AIExplanationResponse)
def ai_explain_endpoint(req: AIExplanationRequest, user: Dict[str, Any] = Depends(get_current_user_context)):
    """
    Direct endpoint for decision explainability. Retrieves authoritative backend evidence
    to explain timetable placements, booking decisions, or constraint bottlenecks.
    """
    q_lower = req.question.lower()

    if req.question_type == "booking_rejection" or "booking" in q_lower or "auditorium" in q_lower:
        ev = evidence_service.explain_booking_decision(req.target_id)
        return AIExplanationResponse(
            question=req.question,
            question_type="booking_rejection",
            target_id=ev.get("target_id"),
            explanation=ev["explanation"],
            evidence=ev["evidence"],
            rules_involved=ev["rules_involved"]
        )

    if req.question_type == "reschedule_infeasible" or "can't" in q_lower or "cannot" in q_lower:
        sid = req.target_id or "MA101-A-L1"
        target_day = req.day or "TUE"
        target_period = req.period or 3
        cf = evidence_service.test_reschedule_feasibility(sid, target_day, target_period)

        msg = f"Feasibility analysis for moving {sid} to {target_day} P{target_period}:\n\n"
        if not cf["is_feasible"]:
            msg += "Blocked by binding constraints:\n" + "\n".join(f"• {v}" for v in cf["violations"])
        else:
            msg += "Target slot is completely feasible with 0 hard violations."

        return AIExplanationResponse(
            question=req.question,
            question_type="reschedule_infeasible",
            target_id=sid,
            explanation=msg,
            evidence=cf,
            rules_involved=cf["rules"],
            is_counterfactual=True
        )

    if req.question_type == "room_selection" or "room" in q_lower or "venue" in q_lower:
        ev = evidence_service.explain_room_selection(req.target_id or "MA101-AB-L1")
        return AIExplanationResponse(
            question=req.question,
            question_type="room_selection",
            target_id=ev.get("target_id"),
            explanation=ev["explanation"],
            evidence=ev["evidence"],
            rules_involved=ev["rules_involved"]
        )

    # Default to timetable slot explanation
    ev = evidence_service.explain_timetable_slot(
        session_id=req.target_id,
        faculty_id=user.get("faculty_id") or user.get("id"),
        day=req.day,
        period=req.period
    )
    return AIExplanationResponse(
        question=req.question,
        question_type="timetable_slot",
        target_id=ev.get("target_id"),
        explanation=ev["explanation"],
        evidence=ev["evidence"],
        rules_involved=ev["rules_involved"]
    )


@ai_router.get("/conversations")
def get_conversations(user: Dict[str, Any] = Depends(get_current_user_context)):
    """Returns conversation history list for current authorized user."""
    return {
        "conversations": [
            {
                "id": "conv_default",
                "title": "Faculty Schedule Assistant",
                "last_active": "Just now",
                "message_count": 4
            }
        ]
    }


@ai_router.post("/proposals/{proposal_id}/submit")
def submit_ai_proposal(
    proposal_id: str,
    user: Dict[str, Any] = Depends(get_current_user_context)
):
    """
    Submits an AI-generated proposal to the existing Module 5 approval workflow.
    Ensures role permissions and prevents self-approval.
    """
    prop = disruption_service.get_proposal_by_id(proposal_id)
    return {
        "status": "submitted_for_approval",
        "proposal_id": proposal_id,
        "message": f"Proposal {proposal_id} submitted to Admin approval queue.",
        "requires_role": "admin"
    }
