from __future__ import annotations

from typing import Any
from ortools.sat.python import cp_model
from backend.exams.context import ExamContext


class ExamVariables:
    """Manages CP-SAT decision variables for the examination scheduling model."""

    def __init__(self, model: cp_model.CpModel, ctx: ExamContext):
        self.model = model
        self.ctx = ctx

        # y[(exam_id, slot_idx)]: 1 if exam is scheduled at slot_idx
        self.exam_slot: dict[tuple[str, int], Any] = {}

        # z[(exam_id, slot_idx, room_id)]: 1 if room_id is used for exam at slot_idx
        self.exam_room: dict[tuple[str, int, str], Any] = {}

        # Day-level excess variables for soft optimization
        self.group_day_excess: dict[tuple[str, int], Any] = {}

        self._create_variables()

    def _create_variables(self):
        num_slots = self.ctx.time_model.total_slots
        room_ids = self.ctx.eligible_room_ids

        for e in self.ctx.raw_exams:
            eid = e["id"]
            for si in range(num_slots):
                self.exam_slot[(eid, si)] = self.model.NewBoolVar(f"slot_{eid}_{si}")
                for rid in room_ids:
                    self.exam_room[(eid, si, rid)] = self.model.NewBoolVar(
                        f"rm_{eid}_{si}_{rid}"
                    )
