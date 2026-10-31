"""
Booking Data Normalizer.
Standardizes user form inputs and AI extracted fields into canonical schema format.
"""

from typing import Dict, Any, List, Optional

VALID_DAYS = {"MON", "TUE", "WED", "THU", "FRI", "SAT"}
VALID_ROOM_TYPES = {
    "auditorium",
    "seminar_hall",
    "lecture_hall",
    "classroom",
    "lab_cs",
    "lab_ee",
    "lab_mech",
    "lab_civil",
    "open_air_theatre"
}


class BookingNormalizer:
    """Normalizes and sanitizes booking input fields."""

    @staticmethod
    def normalize_booking_payload(payload: Dict[str, Any]) -> Dict[str, Any]:
        """Sanitizes and normalizes booking payload."""
        data = dict(payload)

        # Title
        title = str(data.get("title", "Campus Event")).strip()
        data["title"] = title if title else "Campus Event"

        # Requested category
        cat = str(data.get("requested_category", "club_event")).strip().lower()
        if cat not in ["institute_event", "guest_lecture", "department_event", "club_event"]:
            cat = "club_event"
        data["requested_category"] = cat

        # Attendance
        att = int(data.get("attendance", 1))
        data["attendance"] = max(1, att)

        # Duration
        dur = int(data.get("duration_periods", 1))
        data["duration_periods"] = max(1, min(12, dur))

        # Room types
        raw_types = data.get("room_types", [])
        if isinstance(raw_types, str):
            raw_types = [raw_types]
        norm_types = [t.strip().lower() for t in raw_types if t.strip().lower() in VALID_ROOM_TYPES]
        data["room_types"] = norm_types if norm_types else ["classroom"]

        # Windows
        raw_windows = data.get("windows", [])
        norm_windows = []
        for w in raw_windows:
            day = str(w.get("day", "MON")).strip().upper()
            if day not in VALID_DAYS:
                day = "MON"
            fp = max(1, min(13, int(w.get("from_period", 1))))
            tp = max(fp, min(13, int(w.get("to_period", fp + data["duration_periods"] - 1))))
            norm_windows.append({"day": day, "from_period": fp, "to_period": tp})
        if not norm_windows:
            norm_windows = [{"day": "MON", "from_period": 1, "to_period": 1 + data["duration_periods"] - 1}]
        data["windows"] = norm_windows

        # Needs / equipment
        raw_needs = data.get("needs", [])
        if isinstance(raw_needs, str):
            raw_needs = [raw_needs]
        data["needs"] = sorted(list({str(n).strip().lower() for n in raw_needs if str(n).strip()}))

        # Mandatory groups
        raw_groups = data.get("mandatory_for_groups", [])
        if isinstance(raw_groups, str):
            raw_groups = [raw_groups]
        data["mandatory_for_groups"] = sorted(list({str(g).strip().upper() for g in raw_groups if str(g).strip()}))

        # Requested room
        req_room = data.get("requested_room")
        data["requested_room"] = str(req_room).strip().upper() if req_room else None

        return data
