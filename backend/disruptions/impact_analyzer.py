"""
Disruption Impact Analyzer.
Inspects real database timetable records and determines which assignments are invalidated
by reported faculty downtime, room closures, or added/removed sessions.
"""

from typing import Dict, Any, List, Set, Tuple, Optional
from collections import defaultdict


class DisruptionImpactAnalyzer:
    """Analyzes the exact blast radius of a disruption against an approved timetable."""

    @staticmethod
    def analyze_impact(
        disruption_changes: List[Dict[str, Any]],
        baseline_sessions: List[Dict[str, Any]],
        sessions_metadata: Dict[str, Dict[str, Any]],
        exams: Optional[List[Dict[str, Any]]] = None,
        bookings: Optional[List[Dict[str, Any]]] = None
    ) -> Dict[str, Any]:
        """
        Evaluates which baseline sessions collide with disruption changes.
        """
        # Map baseline sessions: sid -> (day, start_p, room_id)
        base_map = {}
        for s in baseline_sessions:
            base_map[s["session_id"]] = (s["day"], s["start_period"], s["room_id"])

        # Track unavailabilities added by disruption
        fac_unavail_added: Set[Tuple[str, str, int]] = set()  # (faculty_id, day, period)
        room_unavail_added: Set[Tuple[str, str, int]] = set()  # (room_id, day, period)
        new_sessions_to_schedule = []
        removed_session_ids = set()

        affected_faculty_set = set()
        affected_rooms_set = set()
        affected_groups_set = set()

        for ch in disruption_changes:
            ch_type = ch.get("type")
            if ch_type == "faculty_unavailable":
                fid = ch["faculty_id"]
                affected_faculty_set.add(fid)
                for day in ch.get("days", []):
                    for p in ch.get("periods", []):
                        fac_unavail_added.add((fid, day, p))

            elif ch_type == "room_unavailable":
                rid = ch["room_id"]
                affected_rooms_set.add(rid)
                for day in ch.get("days", []):
                    for p in ch.get("periods", []):
                        room_unavail_added.add((rid, day, p))

            elif ch_type == "add_session":
                new_s = ch.get("session", {})
                new_sessions_to_schedule.append(new_s)
                if new_s.get("faculty_id"):
                    affected_faculty_set.add(new_s["faculty_id"])
                for g in new_s.get("groups", []):
                    affected_groups_set.add(g)

            elif ch_type == "remove_session":
                removed_session_ids.add(ch.get("session_id"))

        # Find directly affected active sessions
        directly_affected = []
        for sid, (day, start_p, rid) in base_map.items():
            meta = sessions_metadata.get(sid, {})
            fid = meta.get("faculty_id", "")
            dur = meta.get("duration", 1)
            groups = meta.get("groups", [])
            cid = meta.get("course_id", sid)

            is_affected = False
            conflict_type = None
            conflict_detail = None

            # 1. Removed by disruption
            if sid in removed_session_ids:
                is_affected = True
                conflict_type = "removed_session"
                conflict_detail = f"Session {sid} was explicitly removed by disruption."

            # 2. Faculty unavailable
            if not is_affected:
                for p in range(start_p, start_p + dur):
                    if (fid, day, p) in fac_unavail_added:
                        is_affected = True
                        conflict_type = "faculty_unavailable"
                        conflict_detail = f"Faculty {fid} is unavailable on {day} P{p}."
                        break

            # 3. Room closed/unavailable
            if not is_affected:
                for p in range(start_p, start_p + dur):
                    if (rid, day, p) in room_unavail_added:
                        is_affected = True
                        conflict_type = "room_unavailable"
                        conflict_detail = f"Room {rid} is closed/unavailable on {day} P{p}."
                        break

            if is_affected:
                directly_affected.append({
                    "session_id": sid,
                    "course_id": cid,
                    "faculty_id": fid,
                    "groups": groups,
                    "current_day": day,
                    "current_start_period": start_p,
                    "current_room_id": rid,
                    "conflict_type": conflict_type,
                    "conflict_detail": conflict_detail
                })
                affected_faculty_set.add(fid)
                affected_rooms_set.add(rid)
                for g in groups:
                    affected_groups_set.add(g)

        # Exam / Venue Booking collision checks
        exam_conflicts = []
        if exams:
            for aff in directly_affected:
                for ex in exams:
                    if ex.get("day") == aff["current_day"]:
                        overlap_groups = set(aff["groups"]) & set(ex.get("groups", []))
                        if overlap_groups:
                            exam_conflicts.append({
                                "session_id": aff["session_id"],
                                "exam_id": ex.get("exam_id"),
                                "day": ex.get("day"),
                                "overlap_groups": list(overlap_groups)
                            })

        booking_conflicts = []
        if bookings:
            for aff in directly_affected:
                for bk in bookings:
                    if bk.get("status") == "approved" and bk.get("assigned_day") == aff["current_day"] and bk.get("assigned_room_id") == aff["current_room_id"]:
                        booking_conflicts.append({
                            "session_id": aff["session_id"],
                            "booking_id": bk.get("id"),
                            "room_id": bk.get("assigned_room_id"),
                            "day": bk.get("assigned_day")
                        })

        summary_text = (
            f"Disruption directly invalidates {len(directly_affected)} existing timetable assignments "
            f"across {len(affected_faculty_set)} faculty members, {len(affected_rooms_set)} campus rooms, "
            f"and {len(affected_groups_set)} student groups. "
            f"{len(new_sessions_to_schedule)} new sessions require placement."
        )

        return {
            "disruption_id": "analyzed",
            "is_impacted": len(directly_affected) > 0 or len(new_sessions_to_schedule) > 0 or len(removed_session_ids) > 0,
            "total_affected_sessions": len(directly_affected),
            "directly_affected_sessions": directly_affected,
            "affected_faculty": [{"id": fid} for fid in sorted(affected_faculty_set) if fid],
            "affected_rooms": [{"id": rid} for rid in sorted(affected_rooms_set) if rid],
            "affected_student_groups": sorted(list(affected_groups_set)),
            "new_sessions_to_schedule": new_sessions_to_schedule,
            "removed_sessions": sorted(list(removed_session_ids)),
            "exam_conflicts": exam_conflicts,
            "booking_conflicts": booking_conflicts,
            "summary_text": summary_text
        }
