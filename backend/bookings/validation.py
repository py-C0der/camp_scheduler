"""
Deterministic Booking Validation Engine.
Enforces the 10 official hard constraints (H1–H10) and tournament booking rules (B1–B3, H13).
Does not use LLMs for validity or conflict decisions.
"""

from typing import Dict, Any, List, Optional
from backend.bookings.availability import VenueAvailabilityEngine
from backend.bookings.priority import BookingPriorityManager


class BookingValidationEngine:
    """Rigorous Python validation service matching the official tournament validator."""

    def __init__(self, dataset: Dict[str, Any], availability_engine: VenueAvailabilityEngine):
        self.data = dataset
        self.rooms = {r["id"]: r for r in dataset.get("rooms", [])}
        self.availability_engine = availability_engine
        self.priority_manager = BookingPriorityManager(
            dataset.get("priority_order"),
            dataset.get("role_category_cap")
        )

    def validate_request_eligibility(
        self,
        req: Dict[str, Any],
        room_id: str,
        day: str,
        start_period: int,
        ignore_self: bool = True
    ) -> Dict[str, Any]:
        """
        Validates whether assigning room_id on day at start_period is strictly eligible.
        Returns is_valid (bool), list of violations, and detailed reasons.
        """
        violations = []
        conflicts = []

        # Check cancellation (H9 / B3)
        if req.get("is_cancelled") or req.get("status") == "cancelled":
            violations.append(f"Request {req.get('id')} has been cancelled and cannot be allocated.")
            return {
                "is_valid": False,
                "violations": violations,
                "conflicts": conflicts,
                "status_candidate": "rejected",
                "reason": "Request is cancelled"
            }

        # Room existence and event eligibility (H5 / H13)
        room = self.rooms.get(room_id)
        if not room:
            violations.append(f"Unknown room identifier: {room_id}")
            return {
                "is_valid": False,
                "violations": violations,
                "conflicts": conflicts,
                "status_candidate": "rejected",
                "reason": f"Unknown room {room_id}"
            }

        if "event" not in room.get("allowed_uses", []):
            violations.append(f"Room {room_id} is not authorized to host events (allowed: {room.get('allowed_uses')})")

        # Room type compatibility (H5)
        allowed_types = req.get("room_types", [])
        if allowed_types and room.get("type") not in allowed_types:
            violations.append(f"Room {room_id} type '{room.get('type')}' is not one of required {allowed_types}")

        # Room capacity (H4)
        req_attendance = req.get("attendance", 0)
        room_cap = room.get("capacity", 0)
        if room_cap < req_attendance:
            violations.append(f"Room {room_id} capacity ({room_cap}) is insufficient for attendance ({req_attendance})")

        # Room features and equipment (H6)
        required_needs = set(req.get("needs", []))
        room_feats = set(room.get("features", []))
        if room.get("accessible"):
            room_feats.add("accessible")
        missing_feats = sorted(required_needs - room_feats)
        if missing_feats:
            violations.append(f"Room {room_id} lacks required features: {missing_feats}")

        # Duration check (H8)
        dur = req.get("duration_periods", 1)
        end_period = start_period + dur - 1
        max_period = self.data.get("calendar", {}).get("last_teaching_period", 9) + 4  # e.g., 13 periods
        if start_period < 1 or end_period > max_period:
            violations.append(f"Invalid booking duration: P{start_period} to P{end_period} exceeds campus day limits (1..{max_period})")

        # Check requested window match (determines approved vs alternative_offered)
        inside_window = False
        windows = req.get("windows", [])
        for w in windows:
            if w.get("day") == day and w.get("from_period") <= start_period and end_period <= w.get("to_period"):
                inside_window = True
                break

        # Room availability check (H1, H2, H7)
        bid = req.get("id") if ignore_self else None
        room_avail = self.availability_engine.check_room_availability(room_id, day, start_period, dur, ignore_booking_id=bid)
        if not room_avail["available"]:
            for c in room_avail["conflicts"]:
                violations.append(c["detail"])
                conflicts.append(c)

        # Mandatory student groups check (H3)
        mand_groups = req.get("mandatory_for_groups", [])
        if mand_groups:
            grp_avail = self.availability_engine.check_mandatory_groups(mand_groups, day, start_period, dur)
            if not grp_avail["available"]:
                for c in grp_avail["conflicts"]:
                    violations.append(c["detail"])
                    conflicts.append(c)

        is_valid = len(violations) == 0
        candidate_status = "approved" if (is_valid and inside_window) else ("alternative_needed" if is_valid else "rejected")
        primary_reason = violations[0] if violations else ("Approved within requested window" if inside_window else "Viable alternative outside requested window")

        return {
            "is_valid": is_valid,
            "status_candidate": candidate_status,
            "inside_window": inside_window,
            "violations": violations,
            "conflicts": conflicts,
            "reason": primary_reason,
            "capacity_check": {"room_capacity": room_cap, "requested_attendance": req_attendance, "sufficient": room_cap >= req_attendance},
            "feature_check": {"missing_features": missing_feats, "satisfied": len(missing_feats) == 0}
        }
