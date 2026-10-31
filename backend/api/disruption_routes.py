"""
FastAPI REST Router for Module 5: Disruption Management and Timetable Rescheduling Engine.
Implements all 12 Section 10 endpoints with role-based authorization and input validation.
"""

from typing import Dict, Any, List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, Header

from backend.services.disruption_service import DisruptionService
from backend.schemas.disruption import (
    DisruptionCreateRequest,
    DisruptionResponse,
    DisruptionImpactResponse,
    DisruptionDashboardSummary
)
from backend.schemas.rescheduling import (
    RescheduleGenerateRequest,
    ReschedulingProposalResponse,
    ProposalComparisonResponse,
    ProposalDecisionRequest,
    TimetableVersionItem
)

router = APIRouter(tags=["Disruption Management & Rescheduling"])

# Singleton service instance
_disruption_service: Optional[DisruptionService] = None

def get_disruption_service() -> DisruptionService:
    global _disruption_service
    if _disruption_service is None:
        _disruption_service = DisruptionService()
    return _disruption_service


def get_current_user(
    x_user_id: Optional[str] = Header("admin_1"),
    x_user_role: Optional[str] = Header("admin"),
    x_user_name: Optional[str] = Header("Dean Academics (Admin)")
) -> Dict[str, Any]:
    return {
        "id": x_user_id or "admin_1",
        "role": x_user_role or "admin",
        "name": x_user_name or "Dean Academics (Admin)",
        "department": "Dean Office" if x_user_role == "admin" else "CSE"
    }


# 1. GET /api/disruptions/summary
@router.get("/api/disruptions/summary", response_model=DisruptionDashboardSummary)
def get_disruption_dashboard_summary(
    service: DisruptionService = Depends(get_disruption_service)
):
    return service.get_dashboard_summary()


# 2. GET /api/disruptions
@router.get("/api/disruptions", response_model=List[DisruptionResponse])
def list_disruptions(
    service: DisruptionService = Depends(get_disruption_service)
):
    return service.list_disruptions()


# 3. POST /api/disruptions
@router.post("/api/disruptions", response_model=DisruptionResponse)
def create_disruption(
    payload: DisruptionCreateRequest,
    user: Dict[str, Any] = Depends(get_current_user),
    service: DisruptionService = Depends(get_disruption_service)
):
    res = service.create_disruption(payload.dict(), user)
    try:
        from backend.notifications.event_bus import event_bus
        from backend.notifications.events import NotificationEvent, EventTypes
        event_bus.publish(NotificationEvent(
            event_type=EventTypes.DISRUPTION_REPORTED,
            category="disruption",
            severity="critical",
            related_module="module_5",
            related_record_id=res.id,
            published_by=user.get("id", "user"),
            payload={"disruption_id": res.id, "description": res.description}
        ))
    except Exception:
        pass
    return res


# 4. GET /api/disruptions/{id}
@router.get("/api/disruptions/{disruption_id}", response_model=DisruptionResponse)
def get_disruption(
    disruption_id: str,
    service: DisruptionService = Depends(get_disruption_service)
):
    return service.get_disruption_by_id(disruption_id)


# 5. GET /api/disruptions/{id}/impact
@router.get("/api/disruptions/{disruption_id}/impact", response_model=DisruptionImpactResponse)
def analyze_disruption_impact(
    disruption_id: str,
    service: DisruptionService = Depends(get_disruption_service)
):
    return service.analyze_impact(disruption_id)


# 6. POST /api/disruptions/{id}/reschedule
@router.post("/api/disruptions/{disruption_id}/reschedule", response_model=ReschedulingProposalResponse)
def generate_rescheduling_proposal(
    disruption_id: str,
    req: Optional[RescheduleGenerateRequest] = None,
    user: Dict[str, Any] = Depends(get_current_user),
    service: DisruptionService = Depends(get_disruption_service)
):
    t_limit = req.time_limit_seconds if req else 45
    t_name = req.target_version_name if req else None
    res = service.generate_rescheduling_proposal(
        disruption_id=disruption_id,
        user=user,
        time_limit_seconds=t_limit,
        target_version_name=t_name
    )
    try:
        from backend.notifications.event_bus import event_bus
        from backend.notifications.events import NotificationEvent, EventTypes
        event_bus.publish(NotificationEvent(
            event_type=EventTypes.RESCHEDULING_PROPOSED,
            category="disruption",
            severity="high",
            related_module="module_5",
            related_record_id=res.proposal_id,
            published_by=user.get("id", "user"),
            payload={"proposal_id": res.proposal_id, "sessions_moved": res.sessions_moved, "disruption_id": disruption_id}
        ))
    except Exception:
        pass
    return res


# 7. GET /api/rescheduling-proposals
@router.get("/api/rescheduling-proposals", response_model=List[ReschedulingProposalResponse])
def list_rescheduling_proposals(
    disruption_id: Optional[str] = Query(None),
    service: DisruptionService = Depends(get_disruption_service)
):
    return service.list_proposals(disruption_id)


# 8. GET /api/rescheduling-proposals/{id}
@router.get("/api/rescheduling-proposals/{proposal_id}", response_model=ReschedulingProposalResponse)
def get_rescheduling_proposal(
    proposal_id: str,
    service: DisruptionService = Depends(get_disruption_service)
):
    return service.get_proposal_by_id(proposal_id)


# 9. GET /api/rescheduling-proposals/{id}/comparison
@router.get("/api/rescheduling-proposals/{proposal_id}/comparison", response_model=ProposalComparisonResponse)
def get_proposal_comparison(
    proposal_id: str,
    service: DisruptionService = Depends(get_disruption_service)
):
    return service.get_proposal_comparison(proposal_id)


# 10. POST /api/rescheduling-proposals/{id}/approve
@router.post("/api/rescheduling-proposals/{proposal_id}/approve", response_model=ReschedulingProposalResponse)
def approve_rescheduling_proposal(
    proposal_id: str,
    req: Optional[ProposalDecisionRequest] = None,
    user: Dict[str, Any] = Depends(get_current_user),
    service: DisruptionService = Depends(get_disruption_service)
):
    reason = req.reason if req else "Approved by authorized administrator"
    res = service.approve_proposal(proposal_id, user, reason=reason)
    try:
        from backend.notifications.event_bus import event_bus
        from backend.notifications.events import NotificationEvent, EventTypes
        event_bus.publish(NotificationEvent(
            event_type=EventTypes.RESCHEDULING_APPROVED,
            category="disruption",
            severity="critical",
            related_module="module_5",
            related_record_id=proposal_id,
            published_by=user.get("id", "admin"),
            payload={"proposal_id": proposal_id, "sessions_moved": res.sessions_moved}
        ))
    except Exception:
        pass
    return res


# 11. POST /api/rescheduling-proposals/{id}/reject
@router.post("/api/rescheduling-proposals/{proposal_id}/reject", response_model=ReschedulingProposalResponse)
def reject_rescheduling_proposal(
    proposal_id: str,
    req: Optional[ProposalDecisionRequest] = None,
    user: Dict[str, Any] = Depends(get_current_user),
    service: DisruptionService = Depends(get_disruption_service)
):
    reason = req.reason if req else "Rejected by administrator"
    res = service.reject_proposal(proposal_id, user, reason=reason)
    try:
        from backend.notifications.event_bus import event_bus
        from backend.notifications.events import NotificationEvent, EventTypes
        event_bus.publish(NotificationEvent(
            event_type=EventTypes.RESCHEDULING_REJECTED,
            category="disruption",
            severity="medium",
            related_module="module_5",
            related_record_id=proposal_id,
            published_by=user.get("id", "admin"),
            payload={"proposal_id": proposal_id, "reason": reason}
        ))
    except Exception:
        pass
    return res


# 12. GET /api/timetable-versions
@router.get("/api/timetable-versions", response_model=List[TimetableVersionItem])
def get_timetable_versions(
    service: DisruptionService = Depends(get_disruption_service)
):
    return service.get_timetable_versions()
