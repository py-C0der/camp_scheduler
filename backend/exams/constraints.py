from __future__ import annotations

from typing import Any
from ortools.sat.python import cp_model
from backend.exams.context import ExamContext
from backend.exams.variables import ExamVariables


class ExamConstraints:
    """Applies official examination hard and soft constraints to the CP-SAT model."""

    def __init__(self, model: cp_model.CpModel, ctx: ExamContext, vars: ExamVariables):
        self.model = model
        self.ctx = ctx
        self.vars = vars
        self.soft_penalty_terms: list[Any] = []
        self.room_efficiency_terms: list[Any] = []

    def apply_all(self):
        self.apply_exam_assignment_constraint()
        self.apply_room_presence_link()
        self.apply_capacity_constraints()
        self.apply_room_non_overlap()
        self.apply_group_non_overlap()
        self.apply_soft_same_day_group_limits()
        self.apply_room_efficiency_preference()

    def apply_exam_assignment_constraint(self):
        """H1: Every examination must be scheduled in exactly one permitted slot."""
        num_slots = self.ctx.time_model.total_slots
        for e in self.ctx.raw_exams:
            eid = e["id"]
            self.model.AddExactlyOne(
                [self.vars.exam_slot[(eid, si)] for si in range(num_slots)]
            )

    def apply_room_presence_link(self):
        """A room can only be assigned to an exam if the exam is active in that slot."""
        num_slots = self.ctx.time_model.total_slots
        room_ids = self.ctx.eligible_room_ids
        for e in self.ctx.raw_exams:
            eid = e["id"]
            for si in range(num_slots):
                for rid in room_ids:
                    self.model.Add(
                        self.vars.exam_room[(eid, si, rid)]
                        <= self.vars.exam_slot[(eid, si)]
                    )

    def apply_capacity_constraints(self):
        """H4/H5: During examinations, room capacity is halved. Total effective seats >= size."""
        num_slots = self.ctx.time_model.total_slots
        room_ids = self.ctx.eligible_room_ids
        eff_caps = self.ctx.effective_capacities

        for e in self.ctx.raw_exams:
            eid = e["id"]
            size = e["size"]
            for si in range(num_slots):
                seats_sum = sum(
                    self.vars.exam_room[(eid, si, rid)] * eff_caps[rid]
                    for rid in room_ids
                )
                self.model.Add(seats_sum >= size * self.vars.exam_slot[(eid, si)])

    def apply_room_non_overlap(self):
        """H3: A room cannot be allocated to two overlapping examinations."""
        num_slots = self.ctx.time_model.total_slots
        room_ids = self.ctx.eligible_room_ids

        for si in range(num_slots):
            for rid in room_ids:
                self.model.Add(
                    sum(
                        self.vars.exam_room[(e["id"], si, rid)]
                        for e in self.ctx.raw_exams
                    )
                    <= 1
                )

    def apply_group_non_overlap(self):
        """H2: A student group cannot have two examinations in the same slot."""
        num_slots = self.ctx.time_model.total_slots

        for si in range(num_slots):
            for gid, exam_ids in self.ctx.exams_by_group.items():
                if len(exam_ids) > 1:
                    self.model.Add(
                        sum(self.vars.exam_slot[(eid, si)] for eid in exam_ids) <= 1
                    )

    def apply_soft_same_day_group_limits(self):
        """Soft penalty: 5 points for every additional exam a student group has on the same day."""
        for di, day in enumerate(self.ctx.time_model.days):
            day_slot_indices = self.ctx.time_model.get_slots_for_day(day)
            for gid, exam_ids in self.ctx.exams_by_group.items():
                if len(exam_ids) > 1:
                    day_exam_sum = sum(
                        self.vars.exam_slot[(eid, si)]
                        for eid in exam_ids
                        for si in day_slot_indices
                    )
                    excess = self.model.NewIntVar(
                        0, len(exam_ids), f"excess_{gid}_{di}"
                    )
                    self.model.Add(excess >= day_exam_sum - 1)
                    self.model.Add(excess >= 0)
                    self.vars.group_day_excess[(gid, di)] = excess
                    self.soft_penalty_terms.append(5 * excess)

    def apply_room_efficiency_preference(self):
        """Secondary objective: Avoid unnecessarily reserving unneeded rooms."""
        num_slots = self.ctx.time_model.total_slots
        room_ids = self.ctx.eligible_room_ids

        for e in self.ctx.raw_exams:
            eid = e["id"]
            for si in range(num_slots):
                for rid in room_ids:
                    self.room_efficiency_terms.append(
                        self.vars.exam_room[(eid, si, rid)]
                    )
