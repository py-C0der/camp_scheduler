from __future__ import annotations

from typing import Any
from backend.exams.context import ExamContext
from backend.exams.candidates import ExamCandidateManager


class ExamDiagnostics:
    """Provides comprehensive diagnostics for examination scheduling readiness and bottlenecks."""

    def __init__(self, ctx: ExamContext):
        self.ctx = ctx
        self.candidate_mgr = ExamCandidateManager(ctx)

    def run_pre_check(self) -> dict[str, Any]:
        """Perform comprehensive pre-solve structural verification."""
        dataset_errors = self.ctx.validate_dataset()
        profiles = self.candidate_mgr.compute_exam_profiles()

        # Check for groups with more exams than slots
        group_bottlenecks = []
        num_slots = self.ctx.time_model.total_slots
        for gid, eids in self.ctx.exams_by_group.items():
            if len(eids) > num_slots:
                group_bottlenecks.append({
                    "group_id": gid,
                    "exam_count": len(eids),
                    "total_available_slots": num_slots,
                    "message": f"Group {gid} has {len(eids)} exams but only {num_slots} slots exist in exam week.",
                })

        multi_room_exams = [
            p["exam_id"] for p in profiles.values() if p["requires_multi_room"]
        ]

        is_feasible_structurally = len(dataset_errors) == 0 and len(group_bottlenecks) == 0

        return {
            "dataset_id": self.ctx.dataset_id,
            "total_exams": len(self.ctx.raw_exams),
            "eligible_venues": len(self.ctx.eligible_rooms),
            "total_effective_seats_per_slot": self.ctx.total_effective_seats,
            "exam_days": self.ctx.time_model.days,
            "sessions": [s["id"] for s in self.ctx.time_model.sessions],
            "total_slots": num_slots,
            "multi_room_exam_count": len(multi_room_exams),
            "multi_room_exam_ids": multi_room_exams,
            "is_feasible_structurally": is_feasible_structurally,
            "dataset_errors": dataset_errors,
            "group_bottlenecks": group_bottlenecks,
            "profiles": profiles,
        }
