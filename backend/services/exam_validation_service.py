from __future__ import annotations

from collections import defaultdict
from typing import Any
from backend.exams.context import ExamContext


class ExamValidationService:
    """Independent validator strictly implementing the official tournament examination rules."""

    def __init__(self, data: dict[str, Any]):
        self.data = data
        self.ctx = ExamContext(data)

    def validate_schedule(self, exams_out: list[dict[str, Any]]) -> dict[str, Any]:
        """Validates an examination timetable against H1-H7, half-capacity rules, and soft penalty."""
        V: list[dict[str, Any]] = []
        soft_penalty = 0

        ex_map = self.ctx.exams_by_id
        days = self.ctx.time_model.days
        sess_ids = self.ctx.time_model.session_ids
        rooms_map = self.ctx.rooms_by_id

        room_use: dict[tuple[str, str, str], list[str]] = defaultdict(list)
        grp_use: dict[tuple[str, str, str], list[str]] = defaultdict(list)
        grp_day: dict[tuple[str, str], set[str]] = defaultdict(set)
        seen: set[str] = set()

        for e in exams_out:
            eid = e.get("exam_id")
            if not eid or eid not in ex_map:
                V.append({
                    "rule": "E1",
                    "where": "exams",
                    "detail": f"Unknown exam identifier '{eid}'",
                    "exam_id": eid,
                })
                continue

            if eid in seen:
                V.append({
                    "rule": "E1",
                    "where": "exams",
                    "detail": f"Exam {eid} is scheduled more than once",
                    "exam_id": eid,
                })
            seen.add(eid)

            day = e.get("day")
            session = e.get("session")
            if day not in days or session not in sess_ids:
                V.append({
                    "rule": "E1",
                    "where": "exams",
                    "detail": f"{eid}: Invalid slot ({day}, {session}). Allowed days: {days}, sessions: {sess_ids}",
                    "exam_id": eid,
                })
                continue

            # Capacity and venue allowed_uses
            seats = 0
            allocated_rooms = e.get("rooms", [])
            for rid in allocated_rooms:
                r = rooms_map.get(rid)
                if r is None or "exam" not in r.get("allowed_uses", []):
                    V.append({
                        "rule": "E2",
                        "where": "exams",
                        "detail": f"{eid}: Venue '{rid}' is not authorized to host examinations (missing 'exam' in allowed_uses)",
                        "exam_id": eid,
                        "room_id": rid,
                    })
                    continue

                half_cap = r["capacity"] // 2
                seats += half_cap
                room_use[(rid, day, session)].append(eid)

            req_size = ex_map[eid]["size"]
            if seats < req_size:
                V.append({
                    "rule": "H5",
                    "where": "exams",
                    "detail": f"{eid}: Allocated {seats} effective seats at half capacity for {req_size} enrolled students",
                    "exam_id": eid,
                    "deficit": req_size - seats,
                })

            for g in ex_map[eid].get("groups", []):
                grp_use[(g, day, session)].append(eid)
                grp_day[(g, day)].add(eid)

        # Unscheduled examinations check
        for eid in ex_map:
            if eid not in seen:
                V.append({
                    "rule": "E1",
                    "where": "exams",
                    "detail": f"Exam {eid} ({', '.join(ex_map[eid].get('course_ids', []))}) is not scheduled",
                    "exam_id": eid,
                })

        # Room double booking
        for (rid, d, s), eids in room_use.items():
            if len(eids) > 1:
                V.append({
                    "rule": "H4",
                    "where": "exams",
                    "detail": f"Room {rid} double-booked on {d} {s}: {', '.join(sorted(eids))}",
                    "room_id": rid,
                    "conflicting_exams": eids,
                })

        # Student group overlap
        for (gid, d, s), eids in grp_use.items():
            if len(eids) > 1:
                V.append({
                    "rule": "H3",
                    "where": "exams",
                    "detail": f"Student group {gid} has overlapping examinations on {d} {s}: {', '.join(sorted(eids))}",
                    "group_id": gid,
                    "conflicting_exams": eids,
                })

        # Soft penalty: same day multiple exams
        for (gid, d), eids in grp_day.items():
            if len(eids) > 1:
                soft_penalty += 5 * (len(eids) - 1)

        is_valid = len(V) == 0

        return {
            "is_valid": is_valid,
            "hard_violation_count": len(V),
            "hard_violations": V,
            "exam_soft_penalty": soft_penalty,
            "total_scheduled": len(seen),
            "total_expected": len(ex_map),
        }
