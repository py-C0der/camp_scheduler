from __future__ import annotations

from collections import defaultdict
from typing import Any

from backend.exams.time_model import ExamTimeModel


class ExamContext:
    """Manages the full context for examination scheduling."""

    def __init__(self, data: dict[str, Any]):
        self.data = data
        self.dataset_id: str = data.get("dataset_id", "cit-public-v1")

        # Time model
        cal_exam = data.get("calendar", {}).get("exam_week", {})
        self.time_model = ExamTimeModel(cal_exam)

        # Raw datasets
        self.raw_exams: list[dict[str, Any]] = data.get("exams", [])
        self.raw_rooms: list[dict[str, Any]] = data.get("rooms", [])
        self.raw_groups: list[dict[str, Any]] = data.get("student_groups", [])
        self.raw_courses: list[dict[str, Any]] = data.get("courses", [])

        # Filter rooms suitable for exams (allowed_uses must contain 'exam')
        self.eligible_rooms: list[dict[str, Any]] = [
            r for r in self.raw_rooms if "exam" in r.get("allowed_uses", [])
        ]
        self.eligible_room_ids: list[str] = [r["id"] for r in self.eligible_rooms]
        self.rooms_by_id: dict[str, dict[str, Any]] = {
            r["id"]: r for r in self.raw_rooms
        }

        # Half capacity calculation (exact floor division matching validator.py)
        self.effective_capacities: dict[str, int] = {
            r["id"]: r["capacity"] // 2 for r in self.eligible_rooms
        }
        self.total_effective_seats: int = sum(self.effective_capacities.values())

        # Examination mappings
        self.exams_by_id: dict[str, dict[str, Any]] = {
            e["id"]: e for e in self.raw_exams
        }
        self.groups_by_id: dict[str, dict[str, Any]] = {
            g["id"]: g for g in self.raw_groups
        }
        self.courses_by_id: dict[str, dict[str, Any]] = {
            c["id"]: c for c in self.raw_courses
        }

        # Inverted index: student_group_id -> list of exam_ids
        self.exams_by_group: dict[str, list[str]] = defaultdict(list)
        for e in self.raw_exams:
            for gid in e.get("groups", []):
                self.exams_by_group[gid].append(e["id"])

    def validate_dataset(self) -> list[str]:
        """Validate input examination records and venue resources."""
        errors = []
        if not self.raw_exams:
            errors.append("Dataset contains 0 examination records.")
        if not self.eligible_rooms:
            errors.append("No rooms found with 'exam' in allowed_uses.")

        for e in self.raw_exams:
            eid = e.get("id")
            if not eid:
                errors.append(f"Examination record missing 'id': {e}")
                continue
            if not e.get("course_ids"):
                errors.append(f"Exam {eid} has no course_ids.")
            if not e.get("groups"):
                errors.append(f"Exam {eid} has no associated student groups.")
            size = e.get("size", 0)
            if size <= 0:
                errors.append(f"Exam {eid} has non-positive size {size}.")
            if size > self.total_effective_seats:
                errors.append(
                    f"Exam {eid} size ({size}) exceeds total campus exam seating capacity ({self.total_effective_seats})."
                )

        return errors
