from __future__ import annotations

from typing import Any
from backend.exams.context import ExamContext


class ExamRoomAllocator:
    """Manages room allocation calculations, effective seating, and multi-room validation."""

    def __init__(self, ctx: ExamContext):
        self.ctx = ctx

    def calculate_effective_seats(self, room_id: str) -> int:
        """Returns floor(normal_capacity / 2) as required by official examination rules."""
        return self.ctx.effective_capacities.get(room_id, 0)

    def evaluate_allocation(self, room_ids: list[str], required_size: int) -> dict[str, Any]:
        """Calculates total effective seating and breakdown across allocated rooms."""
        rooms_detail = []
        total_seats = 0
        seen = set()
        duplicates = []

        for rid in room_ids:
            if rid in seen:
                duplicates.append(rid)
            seen.add(rid)

            room_info = self.ctx.rooms_by_id.get(rid)
            eff_seats = self.calculate_effective_seats(rid)
            total_seats += eff_seats

            rooms_detail.append({
                "room_id": rid,
                "name": room_info["name"] if room_info else rid,
                "building": room_info.get("building", "") if room_info else "",
                "type": room_info.get("type", "") if room_info else "",
                "normal_capacity": room_info.get("capacity", 0) if room_info else 0,
                "effective_exam_seats": eff_seats,
            })

        is_sufficient = total_seats >= required_size
        return {
            "allocated_rooms": room_ids,
            "room_count": len(room_ids),
            "is_multi_room": len(room_ids) > 1,
            "total_effective_seats": total_seats,
            "required_size": required_size,
            "surplus_seats": max(0, total_seats - required_size),
            "deficit_seats": max(0, required_size - total_seats),
            "is_sufficient": is_sufficient,
            "duplicates": duplicates,
            "breakdown": rooms_detail,
        }
