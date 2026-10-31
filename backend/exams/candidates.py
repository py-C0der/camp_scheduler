from __future__ import annotations

from typing import Any
from backend.exams.context import ExamContext


class ExamCandidateManager:
    """Computes room and slot eligibility profiles for each examination."""

    def __init__(self, ctx: ExamContext):
        self.ctx = ctx

    def compute_exam_profiles(self) -> dict[str, dict[str, Any]]:
        """Classify each exam by capacity needs, multi-room requirement, and eligible venues."""
        profiles = {}
        max_single_room_cap = max(
            self.ctx.effective_capacities.values(), default=0
        )

        for e in self.ctx.raw_exams:
            eid = e["id"]
            size = e["size"]
            requires_multi_room = size > max_single_room_cap

            # Single room candidates
            single_rooms = [
                rid for rid, cap in self.ctx.effective_capacities.items()
                if cap >= size
            ]

            profiles[eid] = {
                "exam_id": eid,
                "size": size,
                "requires_multi_room": requires_multi_room,
                "single_room_candidates": single_rooms,
                "single_room_candidate_count": len(single_rooms),
                "groups": e.get("groups", []),
                "course_ids": e.get("course_ids", []),
                "duration_hours": e.get("duration_hours", 2),
            }

        return profiles
