from __future__ import annotations

from typing import Any


class ExamTimeModel:
    """Encapsulates the examination calendar, days, AM/PM session slots, and intervals."""

    def __init__(self, exam_week_calendar: dict[str, Any]):
        self.calendar_raw = exam_week_calendar
        self.days: list[str] = exam_week_calendar.get(
            "days", ["MON", "TUE", "WED", "THU", "FRI", "SAT"]
        )
        self.sessions: list[dict[str, Any]] = exam_week_calendar.get(
            "sessions",
            [
                {"id": "AM", "start": "09:30", "end": "11:30"},
                {"id": "PM", "start": "14:00", "end": "16:00"},
            ],
        )
        self.session_ids: list[str] = [s["id"] for s in self.sessions]

        # Ordered list of (day, session_id) slots
        self.slots: list[tuple[str, str]] = [
            (day, sess_id) for day in self.days for sess_id in self.session_ids
        ]
        self.slot_indices: dict[tuple[str, str], int] = {
            slot: i for i, slot in enumerate(self.slots)
        }

    @property
    def total_slots(self) -> int:
        return len(self.slots)

    def get_slot(self, index: int) -> tuple[str, str]:
        if 0 <= index < len(self.slots):
            return self.slots[index]
        raise IndexError(f"Slot index {index} out of range (0..{len(self.slots)-1})")

    def get_slot_index(self, day: str, session: str) -> int | None:
        return self.slot_indices.get((day, session))

    def get_slots_for_day(self, day: str) -> list[int]:
        return [
            i for i, (d, _) in enumerate(self.slots) if d == day
        ]

    def get_session_info(self, session_id: str) -> dict[str, Any] | None:
        for s in self.sessions:
            if s["id"] == session_id:
                return s
        return None
