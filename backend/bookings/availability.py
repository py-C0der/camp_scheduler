"""
Room and Venue Availability Engine.
Evaluates room availability against baseline teaching sessions, examinations,
maintenance downtime, and approved bookings.
"""

from typing import Dict, Any, List, Set, Tuple, Optional
from collections import defaultdict


class VenueAvailabilityEngine:
    """Manages multi-period occupancy matrices and collision detection."""

    def __init__(self, dataset: Dict[str, Any]):
        self.data = dataset
        self.rooms: Dict[str, Dict[str, Any]] = {r["id"]: r for r in dataset.get("rooms", [])}
        self.days: List[str] = dataset.get("calendar", {}).get("days", ["MON", "TUE", "WED", "THU", "FRI"])
        
        # Room downtime / maintenance: (room_id, day, period) -> set of reasons
        self.room_maintenance: Set[Tuple[str, str, int]] = set()
        for u in dataset.get("room_unavailability", []):
            rid = u["room_id"]
            d = u["day"]
            for p in u.get("periods", []):
                self.room_maintenance.add((rid, d, p))

        # Academic session occupancy: (room_id, day, period) -> session_id
        self.session_occupancy: Dict[Tuple[str, str, int], str] = {}
        # Student group academic occupancy: (group_id, day, period) -> session_id
        self.group_occupancy: Dict[Tuple[str, str, int], str] = {}

        # Exam occupancy: (room_id, day, period) -> exam_id
        self.exam_occupancy: Dict[Tuple[str, str, int], str] = {}
        # Student group exam occupancy: (group_id, day, period) -> exam_id
        self.group_exam_occupancy: Dict[Tuple[str, str, int], str] = {}

        # Approved bookings occupancy: (room_id, day, period) -> booking_id
        self.booking_occupancy: Dict[Tuple[str, str, int], str] = {}

    def load_academic_timetable(self, assignments: List[Dict[str, Any]]):
        """Loads baseline academic teaching timetable assignments."""
        self.session_occupancy.clear()
        self.group_occupancy.clear()

        sessions_dict = {s["id"]: s for s in self.data.get("sessions", [])}
        for assign in assignments:
            sid = assign.get("session_id")
            day = assign.get("day")
            start_p = assign.get("start_period")
            rid = assign.get("room_id")
            s = sessions_dict.get(sid)
            if not s or not day or not start_p or not rid:
                continue

            dur = s.get("duration", 1)
            groups = s.get("groups", [])
            for p in range(start_p, start_p + dur):
                self.session_occupancy[(rid, day, p)] = sid
                for g in groups:
                    self.group_occupancy[(g, day, p)] = sid

    def load_exam_schedule(self, exam_assignments: List[Dict[str, Any]]):
        """
        Loads mid-semester examination schedule.
        Exams occur in Week 8, but any venue maintenance or overlap checks can be mapped.
        """
        self.exam_occupancy.clear()
        self.group_exam_occupancy.clear()

        # Map exam session periods: AM -> periods 3-4 (09:30-11:30), PM -> periods 6-7 (14:00-16:00)
        exam_session_periods = {
            "AM": [3, 4],
            "PM": [6, 7]
        }
        for ea in exam_assignments:
            exam_id = ea.get("exam_id")
            day = ea.get("day")
            session = ea.get("session")
            rooms = ea.get("rooms", [])
            groups = ea.get("groups", [])
            periods = exam_session_periods.get(session, [3, 4])

            for r in rooms:
                for p in periods:
                    self.exam_occupancy[(r, day, p)] = exam_id
            for g in groups:
                for p in periods:
                    self.group_exam_occupancy[(g, day, p)] = exam_id

    def load_approved_bookings(self, bookings: List[Dict[str, Any]]):
        """Loads already approved event bookings."""
        self.booking_occupancy.clear()
        for b in bookings:
            if b.get("status") != "approved":
                continue
            bid = b.get("request_id") or b.get("id")
            rid = b.get("room_id") or b.get("assigned_room_id")
            day = b.get("day") or b.get("assigned_day")
            sp = b.get("start_period") or b.get("assigned_start_period")
            ep = b.get("end_period") or b.get("assigned_end_period")
            if rid and day and sp and ep:
                for p in range(sp, ep + 1):
                    self.booking_occupancy[(rid, day, p)] = bid

    def check_room_availability(
        self,
        room_id: str,
        day: str,
        start_period: int,
        duration: int,
        ignore_booking_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Checks if room_id is fully available on day for periods [start_period, start_period + duration - 1].
        """
        end_period = start_period + duration - 1
        conflicts = []

        if room_id not in self.rooms:
            return {"available": False, "reason": f"Unknown room {room_id}", "conflicts": ["invalid_room"]}

        room = self.rooms[room_id]
        if "event" not in room.get("allowed_uses", []):
            return {"available": False, "reason": f"Room {room_id} is not authorized for events", "conflicts": ["not_event_room"]}

        for p in range(start_period, end_period + 1):
            # Check maintenance downtime
            if (room_id, day, p) in self.room_maintenance:
                conflicts.append({"type": "maintenance", "day": day, "period": p, "detail": f"{room_id} is under maintenance on {day} P{p}"})

            # Check academic sessions
            if (room_id, day, p) in self.session_occupancy:
                sid = self.session_occupancy[(room_id, day, p)]
                conflicts.append({"type": "teaching_session", "entity_id": sid, "day": day, "period": p, "detail": f"{room_id} occupied by academic class {sid} on {day} P{p}"})

            # Check exams
            if (room_id, day, p) in self.exam_occupancy:
                eid = self.exam_occupancy[(room_id, day, p)]
                conflicts.append({"type": "exam", "entity_id": eid, "day": day, "period": p, "detail": f"{room_id} reserved for exam {eid} on {day} P{p}"})

            # Check existing approved bookings
            if (room_id, day, p) in self.booking_occupancy:
                existing_bid = self.booking_occupancy[(room_id, day, p)]
                if existing_bid != ignore_booking_id:
                    conflicts.append({"type": "booking", "entity_id": existing_bid, "day": day, "period": p, "detail": f"{room_id} booked by {existing_bid} on {day} P{p}"})

        return {
            "available": len(conflicts) == 0,
            "conflicts": conflicts,
            "reason": None if len(conflicts) == 0 else conflicts[0]["detail"]
        }

    def check_mandatory_groups(
        self,
        groups: List[str],
        day: str,
        start_period: int,
        duration: int
    ) -> Dict[str, Any]:
        """Checks if mandatory student groups are free during the requested interval."""
        end_period = start_period + duration - 1
        conflicts = []

        for g in groups:
            for p in range(start_period, end_period + 1):
                if (g, day, p) in self.group_occupancy:
                    sid = self.group_occupancy[(g, day, p)]
                    conflicts.append({"type": "group_class", "group": g, "entity_id": sid, "day": day, "period": p, "detail": f"Group {g} has academic class {sid} on {day} P{p}"})
                if (g, day, p) in self.group_exam_occupancy:
                    eid = self.group_exam_occupancy[(g, day, p)]
                    conflicts.append({"type": "group_exam", "group": g, "entity_id": eid, "day": day, "period": p, "detail": f"Group {g} has exam {eid} on {day} P{p}"})

        return {
            "available": len(conflicts) == 0,
            "conflicts": conflicts,
            "reason": None if len(conflicts) == 0 else conflicts[0]["detail"]
        }
