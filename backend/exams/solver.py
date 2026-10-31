from __future__ import annotations

import time
from typing import Any
from ortools.sat.python import cp_model

from backend.exams.context import ExamContext
from backend.exams.diagnostics import ExamDiagnostics
from backend.exams.variables import ExamVariables
from backend.exams.constraints import ExamConstraints
from backend.exams.room_allocator import ExamRoomAllocator


class ExamCpsatSolver:
    """Mathematical constraint optimization engine for mid-semester examination scheduling."""

    def __init__(self, data: dict[str, Any]):
        self.ctx = ExamContext(data)
        self.diagnostics = ExamDiagnostics(self.ctx)
        self.allocator = ExamRoomAllocator(self.ctx)

    def solve(
        self,
        time_limit_seconds: float = 20.0,
        num_workers: int = 4,
    ) -> dict[str, Any]:
        """Formulate and solve the examination model with OR-Tools CP-SAT."""
        started_at = time.perf_counter()

        # Phase 1: Pre-solve verification
        pre_check = self.diagnostics.run_pre_check()
        if not pre_check["is_feasible_structurally"]:
            return {
                "status": "INFEASIBLE",
                "assignments": [],
                "soft_penalty": 0,
                "solve_time_seconds": round(time.perf_counter() - started_at, 2),
                "message": "Examination model cannot be solved due to structural dataset conflicts.",
                "diagnostics": pre_check,
            }

        # Phase 2: CP-SAT formulation
        model = cp_model.CpModel()
        variables = ExamVariables(model, self.ctx)
        constraints = ExamConstraints(model, self.ctx, variables)
        constraints.apply_all()

        # Minimization objective: Soft same-day double exam penalty (weight 100) + Room efficiency (weight 1)
        objective = (
            sum(constraints.soft_penalty_terms) * 100
            + sum(constraints.room_efficiency_terms)
        )
        model.Minimize(objective)

        # Phase 3: Solve
        solver = cp_model.CpSolver()
        solver.parameters.max_time_in_seconds = float(time_limit_seconds)
        solver.parameters.num_search_workers = int(num_workers)
        solver.parameters.random_seed = 42

        status = solver.Solve(model)
        elapsed = time.perf_counter() - started_at

        status_names = {
            cp_model.OPTIMAL: "OPTIMAL",
            cp_model.FEASIBLE: "FEASIBLE",
            cp_model.INFEASIBLE: "INFEASIBLE",
            cp_model.MODEL_INVALID: "MODEL_INVALID",
            cp_model.UNKNOWN: "UNKNOWN",
        }
        status_name = status_names.get(status, "UNKNOWN")

        if status not in (cp_model.OPTIMAL, cp_model.FEASIBLE):
            return {
                "status": status_name,
                "assignments": [],
                "soft_penalty": 0,
                "solve_time_seconds": round(elapsed, 2),
                "message": f"CP-SAT solver returned {status_name} within {time_limit_seconds}s limit.",
                "diagnostics": pre_check,
            }

        # Phase 4: Extract assignments and verify with room allocator
        assignments = []
        num_slots = self.ctx.time_model.total_slots
        room_ids = self.ctx.eligible_room_ids

        for e in self.ctx.raw_exams:
            eid = e["id"]
            chosen_slot_idx = None
            for si in range(num_slots):
                if solver.Value(variables.exam_slot[(eid, si)]) == 1:
                    chosen_slot_idx = si
                    break

            if chosen_slot_idx is None:
                continue

            day, session = self.ctx.time_model.get_slot(chosen_slot_idx)
            chosen_rooms = [
                rid
                for rid in room_ids
                if solver.Value(variables.exam_room[(eid, chosen_slot_idx, rid)]) == 1
            ]
            chosen_rooms.sort()

            alloc_eval = self.allocator.evaluate_allocation(chosen_rooms, e["size"])

            assignments.append({
                "exam_id": eid,
                "day": day,
                "session": session,
                "rooms": chosen_rooms,
                "student_size": e["size"],
                "total_effective_seats": alloc_eval["total_effective_seats"],
                "is_multi_room": alloc_eval["is_multi_room"],
                "breakdown": alloc_eval["breakdown"],
                "groups": e.get("groups", []),
                "course_ids": e.get("course_ids", []),
                "duration_hours": e.get("duration_hours", 2),
            })

        # Sort assignments by day and session order
        day_order = {d: i for i, d in enumerate(self.ctx.time_model.days)}
        sess_order = {s: i for i, s in enumerate(self.ctx.time_model.session_ids)}
        assignments.sort(
            key=lambda a: (
                day_order.get(a["day"], 99),
                sess_order.get(a["session"], 99),
                a["exam_id"],
            )
        )

        soft_penalty = sum(solver.Value(p) for p in constraints.soft_penalty_terms)

        return {
            "status": status_name,
            "assignments": assignments,
            "exam_count": len(assignments),
            "soft_penalty": soft_penalty,
            "solve_time_seconds": round(elapsed, 2),
            "diagnostics": pre_check,
        }
