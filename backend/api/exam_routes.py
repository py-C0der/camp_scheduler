from __future__ import annotations

import json
from pathlib import Path
from typing import Any
from fastapi import APIRouter, Depends, Header, HTTPException, Query
from fastapi.responses import FileResponse

from backend.schemas.examination import (
    ExamApprovalRequest,
    ExamDetailResponse,
    ExamGenerateRequest,
    ExamListResponse,
    ExamSummaryResponse,
    ExamValidationResponse,
)
from backend.services.exam_export_service import EXAMS_JSON_PATH
from backend.services.exam_service import ExamService

exam_router = APIRouter(prefix="/api/exams", tags=["Examination Management (Module 3)"])

_service: ExamService | None = None


def get_exam_service() -> ExamService:
    global _service
    if _service is None:
        _service = ExamService()
    return _service


def get_current_user_role(x_role: str | None = Header(default="admin")) -> str:
    """Extracts role from header; defaults to admin."""
    return x_role or "admin"


@exam_router.get("/summary", response_model=ExamSummaryResponse)
def get_exam_summary(service: ExamService = Depends(get_exam_service)):
    """Returns examination statistics and KPI metrics."""
    return service.get_summary()


@exam_router.get("", response_model=ExamListResponse)
def list_exams(
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=50, ge=1, le=100),
    day: str | None = Query(default=None),
    course_id: str | None = Query(default=None),
    group_id: str | None = Query(default=None),
    room_id: str | None = Query(default=None),
    session: str | None = Query(default=None),
    status: str | None = Query(default=None),
    service: ExamService = Depends(get_exam_service),
):
    """Returns examination records with pagination and filtering."""
    return service.get_exams(
        page=page,
        limit=limit,
        day=day,
        course_id=course_id,
        group_id=group_id,
        room_id=room_id,
        session=session,
        status=status,
    )


@exam_router.get("/diagnostics")
def get_diagnostics(service: ExamService = Depends(get_exam_service)):
    """Returns examination candidate and structural diagnostics."""
    return service.get_diagnostics()


@exam_router.get("/schedule/latest")
def get_latest_schedule(service: ExamService = Depends(get_exam_service)):
    """Returns the latest examination timetable version."""
    return service.get_latest_schedule()


@exam_router.get("/schedule/{schedule_id}")
def get_schedule_by_id(
    schedule_id: str,
    service: ExamService = Depends(get_exam_service),
):
    """Returns a specific examination timetable version."""
    conn = service.get_connection() if hasattr(service, "get_connection") else None
    from backend.db.database import get_connection
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        "SELECT id, version_number, status, is_active, solver_status, soft_penalty FROM exam_schedule_versions WHERE id = ?",
        (schedule_id,),
    )
    ver = cur.fetchone()
    if not ver:
        conn.close()
        raise HTTPException(status_code=404, detail=f"Schedule version '{schedule_id}' not found.")

    cur.execute(
        "SELECT exam_id, day, session, rooms_json, total_effective_seats, is_multi_room FROM exam_assignments WHERE version_id = ?",
        (schedule_id,),
    )
    assignments = []
    for r in cur.fetchall():
        assignments.append({
            "exam_id": r["exam_id"],
            "day": r["day"],
            "session": r["session"],
            "rooms": json.loads(r["rooms_json"]),
            "total_effective_seats": r["total_effective_seats"],
            "is_multi_room": bool(r["is_multi_room"]),
        })

    conn.close()
    return {
        "version_id": ver["id"],
        "version_number": ver["version_number"],
        "status": ver["status"],
        "is_active": bool(ver["is_active"]),
        "solver_status": ver["solver_status"],
        "soft_penalty": ver["soft_penalty"],
        "assignments": assignments,
    }


@exam_router.get("/{exam_id}", response_model=ExamDetailResponse)
def get_exam_details(
    exam_id: str,
    service: ExamService = Depends(get_exam_service),
):
    """Returns deep room allocation, student count, and capacity breakdown for an examination."""
    detail = service.get_exam_detail(exam_id)
    if not detail:
        raise HTTPException(status_code=404, detail=f"Examination '{exam_id}' not found.")
    return detail


@exam_router.post("/generate")
def generate_exams(
    req: ExamGenerateRequest,
    role: str = Depends(get_current_user_role),
    service: ExamService = Depends(get_exam_service),
):
    """Starts examination timetable generation using CP-SAT constraint optimization."""
    if role not in ("admin", "dean"):
        raise HTTPException(
            status_code=403,
            detail="Forbidden: Only an authorized Administrator can generate examination timetables.",
        )

    res = service.generate_schedule(
        time_limit_seconds=req.time_limit_seconds,
        num_workers=req.num_workers,
        created_by=role,
    )

    if not res.get("success"):
        raise HTTPException(status_code=422, detail=res)

    return res


@exam_router.post("/validate", response_model=ExamValidationResponse)
def validate_exam_schedule(
    service: ExamService = Depends(get_exam_service),
):
    """Validates the active or latest examination schedule against official rules."""
    latest = service.get_latest_schedule()
    assignments = latest.get("assignments", [])
    if not assignments:
        # Fallback to dataset default
        exams_list = service.get_exams(limit=100)["items"]
        assignments = [e for e in exams_list if e.get("day")]

    report = service.validator.validate_schedule(assignments)
    return {
        "valid": report["is_valid"],
        "hard_violation_count": report["hard_violation_count"],
        "hard_violations": report["hard_violations"],
        "exam_soft_penalty": report["exam_soft_penalty"],
    }


@exam_router.post("/schedule/{schedule_id}/approve")
def approve_schedule(
    schedule_id: str,
    req: ExamApprovalRequest,
    role: str = Depends(get_current_user_role),
    service: ExamService = Depends(get_exam_service),
):
    """Allows an authorized Admin to approve a proposed examination timetable version."""
    if role not in ("admin", "dean"):
        raise HTTPException(
            status_code=403,
            detail="Forbidden: Only an Administrator can approve examination schedules.",
        )

    try:
        res = service.approve_schedule(
            version_id=schedule_id,
            approved_by=req.approved_by or role,
            note=req.note,
        )
        return res
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to approve examination schedule: {exc}")


# Standalone export endpoint required in Section 10: GET /api/export/exams
export_exam_router = APIRouter(prefix="/api/export", tags=["Exports"])


@export_exam_router.get("/exams")
def export_exams(service: ExamService = Depends(get_exam_service)):
    """Exports examination assignments in the official required format."""
    latest = service.get_latest_schedule()
    assignments = latest.get("assignments", [])
    if not assignments:
        exams_list = service.get_exams(limit=100)["items"]
        assignments = [e for e in exams_list if e.get("day")]

    from backend.services.exam_export_service import ExamExportService
    official_data = ExamExportService.format_official_exams(assignments)
    ExamExportService.sync_to_schedule_export(assignments)

    if EXAMS_JSON_PATH.exists():
        return FileResponse(EXAMS_JSON_PATH, media_type="application/json", filename="exams.json")
    return official_data
