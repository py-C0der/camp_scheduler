"""
FastAPI REST Router for Module 4: Smart Venue Booking and Approval Management System.
Implements all 18 Section 15 endpoints with role-based authorization and input validation.
"""

from typing import Dict, Any, List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, Header
from pydantic import BaseModel

from backend.services.booking_service import BookingService
from backend.services.booking_export_service import BookingExportService
from backend.schemas.booking import (
    BookingParseRequest,
    BookingDraftResponse,
    BookingCreateRequest,
    BookingUpdateRequest,
    BookingRecordResponse,
    BookingSummaryResponse
)
from backend.schemas.booking_decision import (
    BookingApproveRequest,
    BookingRejectRequest,
    BookingAcceptAlternativeRequest,
    BookingCancellationRequest,
    PriorityConfigResponse,
    PriorityConfigUpdate
)

router = APIRouter(prefix="/api/bookings", tags=["Venue Bookings"])
booking_export_router = APIRouter(prefix="/api/export/bookings", tags=["Exports"])

# Singleton service instance
_booking_service: Optional[BookingService] = None

def get_booking_service() -> BookingService:
    global _booking_service
    if _booking_service is None:
        _booking_service = BookingService()
        _booking_service.initialize_and_sync()
    return _booking_service


def get_current_user(
    x_user_id: Optional[str] = Header("admin_1"),
    x_user_role: Optional[str] = Header("admin"),
    x_user_name: Optional[str] = Header("Dean Academics (Admin)")
) -> Dict[str, Any]:
    """Extracts simulated authenticated user from headers."""
    return {
        "id": x_user_id or "admin_1",
        "role": x_user_role or "admin",
        "name": x_user_name or "Dean Academics (Admin)",
        "department": "Dean Office" if x_user_role == "admin" else "CSE"
    }


# 1. GET /api/bookings/summary
@router.get("/summary", response_model=BookingSummaryResponse)
def get_bookings_summary(service: BookingService = Depends(get_booking_service)):
    return service.get_summary()


# 2. GET /api/bookings
@router.get("")
def list_bookings(
    category: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    day: Optional[str] = Query(None),
    room_id: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    service: BookingService = Depends(get_booking_service)
):
    return service.list_bookings(
        category=category,
        status=status,
        day=day,
        room_id=room_id,
        search=search,
        limit=limit,
        offset=offset
    )


# 3. GET /api/bookings/priority
@router.get("/priority", response_model=PriorityConfigResponse)
def get_priority_configuration(service: BookingService = Depends(get_booking_service)):
    return service.get_priority_configuration()


# 4. PATCH /api/bookings/priority
@router.patch("/priority", response_model=PriorityConfigResponse)
def update_priority_configuration(
    payload: PriorityConfigUpdate,
    user: Dict[str, Any] = Depends(get_current_user),
    service: BookingService = Depends(get_booking_service)
):
    return service.update_priority_configuration(
        new_order=payload.priority_order,
        new_caps=payload.role_category_cap,
        user=user
    )


# 5. GET /api/bookings/availability
@router.get("/availability")
def check_room_availability(
    room_id: str = Query(...),
    day: str = Query(...),
    start_period: int = Query(..., ge=1, le=13),
    duration: int = Query(1, ge=1, le=13),
    service: BookingService = Depends(get_booking_service)
):
    return service.availability_engine.check_room_availability(
        room_id=room_id,
        day=day,
        start_period=start_period,
        duration=duration
    )


# 6. GET /api/bookings/conflicts
@router.get("/conflicts")
def get_booking_conflicts(
    room_id: Optional[str] = Query(None),
    day: Optional[str] = Query(None),
    service: BookingService = Depends(get_booking_service)
):
    """Returns all current occupied room periods across bookings, sessions, and maintenance."""
    conflicts = []
    # Room maintenance
    for rid, d, p in service.availability_engine.room_maintenance:
        if (not room_id or rid == room_id) and (not day or d == day):
            conflicts.append({"room_id": rid, "day": d, "period": p, "type": "maintenance"})
    # Academic sessions
    for (rid, d, p), sid in service.availability_engine.session_occupancy.items():
        if (not room_id or rid == room_id) and (not day or d == day):
            conflicts.append({"room_id": rid, "day": d, "period": p, "type": "teaching_session", "entity": sid})
    # Approved bookings
    for (rid, d, p), bid in service.availability_engine.booking_occupancy.items():
        if (not room_id or rid == room_id) and (not day or d == day):
            conflicts.append({"room_id": rid, "day": d, "period": p, "type": "booking", "entity": bid})

    return {"total_conflicts": len(conflicts), "conflicts": conflicts}


# 7. POST /api/bookings/parse
@router.post("/parse", response_model=BookingDraftResponse)
def parse_natural_language_booking(
    req: BookingParseRequest,
    user: Dict[str, Any] = Depends(get_current_user),
    service: BookingService = Depends(get_booking_service)
):
    role = req.user_role or user.get("role", "club")
    return service.parse_natural_language_request(req.text, user_role=role, department=req.department)


# 8. POST /api/bookings
@router.post("", response_model=BookingRecordResponse)
def create_booking(
    req: BookingCreateRequest,
    user: Dict[str, Any] = Depends(get_current_user),
    service: BookingService = Depends(get_booking_service)
):
    res = service.create_booking(req.dict(), user)
    try:
        from backend.notifications.event_bus import event_bus
        from backend.notifications.events import NotificationEvent, EventTypes
        event_bus.publish(NotificationEvent(
            event_type=EventTypes.BOOKING_SUBMITTED,
            category="venue_booking",
            severity="medium",
            related_module="module_4",
            related_record_id=res.get("id"),
            published_by=user.get("id", "user"),
            payload={"booking_id": res.get("id"), "requester": res.get("requester"), "category": res.get("effective_category")}
        ))
    except Exception:
        pass
    return res


# 9. POST /api/bookings/decide-all (Batch process Spectra-week requests)
@router.post("/decide-all")
def decide_all_spectra_bookings(
    service: BookingService = Depends(get_booking_service)
):
    return service.decide_all_spectra_bookings()


# 10. GET /api/bookings/{booking_id}
@router.get("/{booking_id}")
def get_booking_details(
    booking_id: str,
    service: BookingService = Depends(get_booking_service)
):
    return service.get_booking_by_id(booking_id)


# 11. PATCH /api/bookings/{booking_id}
@router.patch("/{booking_id}")
def update_booking(
    booking_id: str,
    req: BookingUpdateRequest,
    user: Dict[str, Any] = Depends(get_current_user),
    service: BookingService = Depends(get_booking_service)
):
    return service.update_booking(booking_id, req.dict(), user)


# 12. POST /api/bookings/{booking_id}/validate
@router.post("/{booking_id}/validate")
def validate_booking(
    booking_id: str,
    room_id: Optional[str] = Query(None),
    day: Optional[str] = Query(None),
    start_period: Optional[int] = Query(None),
    service: BookingService = Depends(get_booking_service)
):
    return service.validate_booking(booking_id, room_id, day, start_period)


# 13. POST /api/bookings/{booking_id}/decide
@router.post("/{booking_id}/decide")
def decide_single_booking(
    booking_id: str,
    user: Dict[str, Any] = Depends(get_current_user),
    service: BookingService = Depends(get_booking_service)
):
    # Runs the global priority resolution to evaluate this booking in context
    res = service.decide_all_spectra_bookings()
    dec = next((d for d in res["decisions"] if d.get("request_id") == booking_id), None)
    return {
        "booking_id": booking_id,
        "decision": dec,
        "current_state": service.get_booking_by_id(booking_id)
    }


# 14. POST /api/bookings/{booking_id}/approve
@router.post("/{booking_id}/approve")
def approve_booking(
    booking_id: str,
    req: Optional[BookingApproveRequest] = None,
    user: Dict[str, Any] = Depends(get_current_user),
    service: BookingService = Depends(get_booking_service)
):
    r_id = req.room_id if req else None
    d_str = req.day if req else None
    s_p = req.start_period if req else None
    reason = req.reason if req else None
    res = service.approve_booking(booking_id, user, room_id=r_id, day=d_str, start_period=s_p, reason=reason)
    try:
        from backend.notifications.event_bus import event_bus
        from backend.notifications.events import NotificationEvent, EventTypes
        event_bus.publish(NotificationEvent(
            event_type=EventTypes.BOOKING_APPROVED,
            category="venue_booking",
            severity="medium",
            related_module="module_4",
            related_record_id=booking_id,
            published_by=user.get("id", "admin"),
            payload={"booking_id": booking_id, "room_id": r_id or res.get("assigned_room_id"), "day": d_str or res.get("assigned_day"), "start_period": s_p or res.get("assigned_start_period"), "end_period": res.get("assigned_end_period"), "reason": reason or res.get("decision_reason")}
        ))
    except Exception:
        pass
    return res


# 15. POST /api/bookings/{booking_id}/reject
@router.post("/{booking_id}/reject")
def reject_booking(
    booking_id: str,
    req: BookingRejectRequest,
    user: Dict[str, Any] = Depends(get_current_user),
    service: BookingService = Depends(get_booking_service)
):
    res = service.reject_booking(booking_id, user, reason=req.reason)
    try:
        from backend.notifications.event_bus import event_bus
        from backend.notifications.events import NotificationEvent, EventTypes
        event_bus.publish(NotificationEvent(
            event_type=EventTypes.BOOKING_REJECTED,
            category="venue_booking",
            severity="medium",
            related_module="module_4",
            related_record_id=booking_id,
            published_by=user.get("id", "admin"),
            payload={"booking_id": booking_id, "reason": req.reason}
        ))
    except Exception:
        pass
    return res


# 16. POST /api/bookings/{booking_id}/alternatives
@router.post("/{booking_id}/alternatives")
def get_alternatives(
    booking_id: str,
    service: BookingService = Depends(get_booking_service)
):
    return service.generate_alternatives(booking_id)


# 17. POST /api/bookings/{booking_id}/accept-alternative
@router.post("/{booking_id}/accept-alternative")
def accept_alternative(
    booking_id: str,
    req: Optional[BookingAcceptAlternativeRequest] = None,
    user: Dict[str, Any] = Depends(get_current_user),
    service: BookingService = Depends(get_booking_service)
):
    alt_id = req.alternative_id if req else None
    r_id = req.room_id if req else None
    d_str = req.day if req else None
    s_p = req.start_period if req else None
    return service.accept_alternative(booking_id, user, alternative_id=alt_id, room_id=r_id, day=d_str, start_period=s_p)


# 18. POST /api/bookings/{booking_id}/cancel
@router.post("/{booking_id}/cancel")
def cancel_booking(
    booking_id: str,
    req: Optional[BookingCancellationRequest] = None,
    user: Dict[str, Any] = Depends(get_current_user),
    service: BookingService = Depends(get_booking_service)
):
    reason = req.reason if req else "Cancelled by user"
    res = service.cancel_booking(booking_id, user, reason=reason)
    try:
        from backend.notifications.event_bus import event_bus
        from backend.notifications.events import NotificationEvent, EventTypes
        event_bus.publish(NotificationEvent(
            event_type=EventTypes.BOOKING_CANCELLED,
            category="venue_booking",
            severity="low",
            related_module="module_4",
            related_record_id=booking_id,
            published_by=user.get("id", "user"),
            payload={"booking_id": booking_id, "reason": reason}
        ))
    except Exception:
        pass
    return res


# 19. GET /api/export/bookings
@booking_export_router.get("")
def export_booking_decisions():
    return BookingExportService.export_booking_decisions()
