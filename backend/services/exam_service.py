from __future__ import annotations

import json
from pathlib import Path
from typing import Any
from backend.db.database import get_connection
from backend.exams.context import ExamContext
from backend.exams.diagnostics import ExamDiagnostics
from backend.exams.room_allocator import ExamRoomAllocator
from backend.exams.solver import ExamCpsatSolver
from backend.services.exam_export_service import ExamExportService
from backend.services.exam_validation_service import ExamValidationService

DATA_PATH = Path(__file__).resolve().parent.parent.parent / "CrunchWeek_StarterPack" / "data" / "cit_public.json"


def load_raw_dataset() -> dict[str, Any]:
    with DATA_PATH.open("r", encoding="utf-8") as f:
        return json.load(f)


class ExamService:
    """Core domain service for examination scheduling, database versioning, approval and queries."""

    def __init__(self):
        self.data = load_raw_dataset()
        self.ctx = ExamContext(self.data)
        self.allocator = ExamRoomAllocator(self.ctx)
        self.validator = ExamValidationService(self.data)

    def get_summary(self) -> dict[str, Any]:
        """Returns comprehensive KPI metrics for examination management dashboard."""
        conn = get_connection()
        cur = conn.cursor()

        # Check for active approved version or latest proposed
        cur.execute(
            "SELECT id, version_number, status, is_active, soft_penalty FROM exam_schedule_versions ORDER BY version_number DESC LIMIT 1"
        )
        latest_ver = cur.fetchone()

        total_exams = len(self.ctx.raw_exams)
        scheduled = 0
        unscheduled = total_exams
        multi_room_count = 0
        total_allocated_rooms = 0
        pending_approval = False
        val_status = "PENDING"
        soft_penalty = 0
        version_id = None

        if latest_ver:
            version_id = latest_ver["id"]
            soft_penalty = latest_ver["soft_penalty"]
            if latest_ver["status"] == "proposed":
                pending_approval = True

            cur.execute(
                "SELECT COUNT(*) FROM exam_assignments WHERE version_id = ?",
                (version_id,),
            )
            scheduled = cur.fetchone()[0]
            unscheduled = max(0, total_exams - scheduled)

            cur.execute(
                "SELECT COUNT(*) FROM exam_assignments WHERE version_id = ? AND is_multi_room = 1",
                (version_id,),
            )
            multi_room_count = cur.fetchone()[0]

            cur.execute(
                "SELECT rooms_json FROM exam_assignments WHERE version_id = ?",
                (version_id,),
            )
            all_rooms = set()
            for row in cur.fetchall():
                rooms = json.loads(row["rooms_json"])
                all_rooms.update(rooms)
            total_allocated_rooms = len(all_rooms)

            cur.execute(
                "SELECT is_valid FROM exam_validation_reports WHERE version_id = ? ORDER BY id DESC LIMIT 1",
                (version_id,),
            )
            val_row = cur.fetchone()
            if val_row:
                val_status = "VALID" if val_row["is_valid"] == 1 else "FAILED"
        else:
            # Check legacy exam_schedules if present
            cur.execute(
                "SELECT COUNT(*) FROM exam_schedules WHERE day IS NOT NULL"
            )
            scheduled = cur.fetchone()[0]
            unscheduled = max(0, total_exams - scheduled)

        conn.close()

        return {
            "total_exams": total_exams,
            "scheduled_exams": scheduled,
            "unscheduled_exams": unscheduled,
            "total_allocated_rooms": total_allocated_rooms,
            "multi_room_exams": multi_room_count,
            "pending_approval": pending_approval,
            "validation_status": val_status,
            "exam_soft_penalty": soft_penalty,
            "latest_schedule_version": version_id,
            "exam_days": self.ctx.time_model.days,
            "exam_sessions": self.ctx.time_model.sessions,
        }

    def get_exams(
        self,
        page: int = 1,
        limit: int = 50,
        day: str | None = None,
        course_id: str | None = None,
        group_id: str | None = None,
        room_id: str | None = None,
        session: str | None = None,
        status: str | None = None,
    ) -> dict[str, Any]:
        """Returns paginated and filtered examination records."""
        conn = get_connection()
        cur = conn.cursor()

        # Find active version, or fallback to proposed
        cur.execute(
            "SELECT id FROM exam_schedule_versions WHERE is_active = 1 LIMIT 1"
        )
        active_row = cur.fetchone()
        if not active_row:
            cur.execute(
                "SELECT id FROM exam_schedule_versions ORDER BY version_number DESC LIMIT 1"
            )
            active_row = cur.fetchone()

        version_id = active_row["id"] if active_row else None

        assignments_by_exam = {}
        if version_id:
            cur.execute(
                "SELECT exam_id, day, session, rooms_json, total_effective_seats, is_multi_room FROM exam_assignments WHERE version_id = ?",
                (version_id,),
            )
            for row in cur.fetchall():
                assignments_by_exam[row["exam_id"]] = {
                    "day": row["day"],
                    "session": row["session"],
                    "rooms": json.loads(row["rooms_json"]),
                    "total_effective_seats": row["total_effective_seats"],
                    "is_multi_room": bool(row["is_multi_room"]),
                }
        else:
            cur.execute(
                "SELECT exam_id, day, session, rooms_json FROM exam_schedules"
            )
            for row in cur.fetchall():
                rooms = json.loads(row["rooms_json"]) if row["rooms_json"] else []
                seats = sum(self.ctx.effective_capacities.get(r, 0) for r in rooms)
                assignments_by_exam[row["exam_id"]] = {
                    "day": row["day"],
                    "session": row["session"],
                    "rooms": rooms,
                    "total_effective_seats": seats,
                    "is_multi_room": len(rooms) > 1,
                }

        conn.close()

        records = []
        for e in self.ctx.raw_exams:
            eid = e["id"]
            assign = assignments_by_exam.get(eid)

            item = {
                "exam_id": eid,
                "course_ids": e.get("course_ids", []),
                "groups": e.get("groups", []),
                "size": e["size"],
                "duration_hours": e.get("duration_hours", 2),
                "day": assign["day"] if assign else None,
                "session": assign["session"] if assign else None,
                "rooms": assign["rooms"] if assign else [],
                "total_effective_seats": assign["total_effective_seats"] if assign else 0,
                "is_multi_room": assign["is_multi_room"] if assign else False,
                "status": "scheduled" if (assign and assign["day"]) else "unscheduled",
            }

            # Filter checks
            if day and item["day"] != day:
                continue
            if session and item["session"] != session:
                continue
            if course_id and not any(course_id.lower() in c.lower() for c in item["course_ids"]):
                continue
            if group_id and group_id not in item["groups"]:
                continue
            if room_id and room_id not in item["rooms"]:
                continue
            if status and item["status"] != status:
                continue

            records.append(item)

        total = len(records)
        start = (page - 1) * limit
        end = start + limit
        paginated = records[start:end]

        return {
            "total": total,
            "page": page,
            "limit": limit,
            "items": paginated,
        }

    def get_exam_detail(self, exam_id: str) -> dict[str, Any] | None:
        """Returns deep room allocation details, seating breakdown, and validation for a specific exam."""
        e = self.ctx.exams_by_id.get(exam_id)
        if not e:
            return None

        summary = self.get_exams(limit=100)
        matched = next((x for x in summary["items"] if x["exam_id"] == exam_id), None)
        rooms = matched["rooms"] if matched else []

        eval_res = self.allocator.evaluate_allocation(rooms, e["size"])

        return {
            "exam_id": exam_id,
            "course_ids": e.get("course_ids", []),
            "groups": e.get("groups", []),
            "size": e["size"],
            "duration_hours": e.get("duration_hours", 2),
            "day": matched["day"] if matched else None,
            "session": matched["session"] if matched else None,
            "rooms": rooms,
            "total_effective_seats": eval_res["total_effective_seats"],
            "is_multi_room": eval_res["is_multi_room"],
            "surplus_seats": eval_res["surplus_seats"],
            "breakdown": eval_res["breakdown"],
            "validation_status": "VALID" if eval_res["is_sufficient"] else "INSUFFICIENT_CAPACITY",
        }

    def generate_schedule(
        self,
        time_limit_seconds: float = 20.0,
        num_workers: int = 4,
        created_by: str = "admin",
    ) -> dict[str, Any]:
        """Runs the CP-SAT examination solver, builds a proposal version, and records independent validation."""
        solver = ExamCpsatSolver(self.data)
        res = solver.solve(
            time_limit_seconds=time_limit_seconds, num_workers=num_workers
        )

        if res["status"] not in ("OPTIMAL", "FEASIBLE"):
            return {
                "success": False,
                "status": res["status"],
                "message": res.get("message", "Solver failed to find a valid examination timetable."),
                "diagnostics": res.get("diagnostics"),
            }

        assignments = res["assignments"]

        # Run independent validation
        val_report = self.validator.validate_schedule(assignments)

        conn = get_connection()
        cur = conn.cursor()

        # Get next version number
        cur.execute("SELECT COALESCE(MAX(version_number), 0) + 1 FROM exam_schedule_versions")
        next_ver_num = cur.fetchone()[0]
        version_id = f"exam_v{next_ver_num}"

        # Insert proposed version
        cur.execute(
            """
            INSERT INTO exam_schedule_versions (id, version_number, status, is_active, solver_status, solve_time_seconds, soft_penalty, created_by)
            VALUES (?, ?, 'proposed', 0, ?, ?, ?, ?)
            """,
            (
                version_id,
                next_ver_num,
                res["status"],
                res["solve_time_seconds"],
                res["soft_penalty"],
                created_by,
            ),
        )

        # Insert assignments
        for a in assignments:
            cur.execute(
                """
                INSERT INTO exam_assignments (version_id, exam_id, day, session, rooms_json, total_effective_seats, is_multi_room)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    version_id,
                    a["exam_id"],
                    a["day"],
                    a["session"],
                    json.dumps(a["rooms"]),
                    a["total_effective_seats"],
                    1 if a["is_multi_room"] else 0,
                ),
            )

        # Record validation report
        cur.execute(
            """
            INSERT INTO exam_validation_reports (version_id, is_valid, hard_violation_count, hard_violations_json, soft_penalty)
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                version_id,
                1 if val_report["is_valid"] else 0,
                val_report["hard_violation_count"],
                json.dumps(val_report["hard_violations"]),
                val_report["exam_soft_penalty"],
            ),
        )

        conn.commit()
        conn.close()

        return {
            "success": True,
            "version_id": version_id,
            "version_number": next_ver_num,
            "status": res["status"],
            "solve_time_seconds": res["solve_time_seconds"],
            "soft_penalty": res["soft_penalty"],
            "assignments_count": len(assignments),
            "validation": val_report,
            "proposal_ready_for_approval": True,
        }

    def approve_schedule(
        self,
        version_id: str,
        approved_by: str = "admin",
        note: str | None = None,
    ) -> dict[str, Any]:
        """Admin approves a proposed examination schedule version and commits it to exports/schedule.json."""
        conn = get_connection()
        cur = conn.cursor()

        cur.execute(
            "SELECT id, version_number, status, soft_penalty FROM exam_schedule_versions WHERE id = ?",
            (version_id,),
        )
        ver = cur.fetchone()
        if not ver:
            conn.close()
            raise ValueError(f"Examination schedule version '{version_id}' does not exist.")

        # Deactivate all previous versions
        cur.execute("UPDATE exam_schedule_versions SET is_active = 0 WHERE is_active = 1")

        # Mark this version approved and active
        cur.execute(
            "UPDATE exam_schedule_versions SET status = 'approved', is_active = 1 WHERE id = ?",
            (version_id,),
        )

        # Record approval
        cur.execute(
            """
            INSERT INTO exam_approvals (version_id, approved_by, approval_notes)
            VALUES (?, ?, ?)
            """,
            (version_id, approved_by, note or f"Approved by {approved_by}"),
        )

        # Fetch assignments for synchronization
        cur.execute(
            "SELECT exam_id, day, session, rooms_json, total_effective_seats FROM exam_assignments WHERE version_id = ?",
            (version_id,),
        )
        rows = cur.fetchall()
        assignments = []
        for r in rows:
            rooms = json.loads(r["rooms_json"])
            assignments.append({
                "exam_id": r["exam_id"],
                "day": r["day"],
                "session": r["session"],
                "rooms": rooms,
            })
            # Sync to exam_schedules table
            cur.execute(
                """
                UPDATE exam_schedules
                SET day = ?, session = ?, rooms_json = ?
                WHERE exam_id = ?
                """,
                (r["day"], r["session"], r["rooms_json"], r["exam_id"]),
            )

        conn.commit()
        conn.close()

        # Export and sync to exports/schedule.json
        export_res = ExamExportService.sync_to_schedule_export(assignments)

        return {
            "success": True,
            "approved_version_id": version_id,
            "version_number": ver["version_number"],
            "approved_by": approved_by,
            "export_sync": export_res,
        }

    def get_latest_schedule(self) -> dict[str, Any]:
        """Retrieves the currently active or latest proposed examination schedule."""
        conn = get_connection()
        cur = conn.cursor()

        cur.execute(
            "SELECT id, version_number, status, is_active, solver_status, soft_penalty FROM exam_schedule_versions WHERE is_active = 1 LIMIT 1"
        )
        ver = cur.fetchone()
        if not ver:
            cur.execute(
                "SELECT id, version_number, status, is_active, solver_status, soft_penalty FROM exam_schedule_versions ORDER BY version_number DESC LIMIT 1"
            )
            ver = cur.fetchone()

        if not ver:
            conn.close()
            return {"schedule": None, "assignments": []}

        version_id = ver["id"]
        cur.execute(
            "SELECT exam_id, day, session, rooms_json, total_effective_seats, is_multi_room FROM exam_assignments WHERE version_id = ?",
            (version_id,),
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
            "version_id": version_id,
            "version_number": ver["version_number"],
            "status": ver["status"],
            "is_active": bool(ver["is_active"]),
            "soft_penalty": ver["soft_penalty"],
            "assignments": assignments,
        }

    def get_diagnostics(self) -> dict[str, Any]:
        """Returns deep structural diagnostics and bottlenecks."""
        diag = ExamDiagnostics(self.ctx)
        return diag.run_pre_check()
