"""
Alternative Venue and Time Slot Generation Engine.
Finds feasible, non-conflicting alternatives when an original request cannot be fulfilled as requested.
Only suggests options that strictly satisfy all hard constraints.
"""

from typing import Dict, Any, List, Optional
from backend.bookings.availability import VenueAvailabilityEngine
from backend.bookings.validation import BookingValidationEngine


class BookingAlternativeEngine:
    """Explores eligible rooms and candidate time windows for feasible alternatives."""

    def __init__(
        self,
        dataset: Dict[str, Any],
        availability_engine: VenueAvailabilityEngine,
        validation_engine: BookingValidationEngine
    ):
        self.data = dataset
        self.rooms = {r["id"]: r for r in dataset.get("rooms", [])}
        self.days = dataset.get("calendar", {}).get("days", ["MON", "TUE", "WED", "THU", "FRI"])
        self.max_period = dataset.get("calendar", {}).get("last_teaching_period", 9) + 4  # 13 periods
        self.availability_engine = availability_engine
        self.validation_engine = validation_engine

    def find_alternatives(
        self,
        req: Dict[str, Any],
        max_suggestions: int = 5
    ) -> List[Dict[str, Any]]:
        """
        Searches for valid alternative placements:
        Priority 1: Same day within or near requested window in an alternative eligible room.
        Priority 2: Same room on another day/slot.
        Priority 3: Other eligible rooms on other days.
        """
        if req.get("is_cancelled") or req.get("status") == "cancelled":
            return []

        dur = req.get("duration_periods", 1)
        attendance = req.get("attendance", 0)
        req_types = req.get("room_types", [])
        needs = set(req.get("needs", []))
        mand_groups = req.get("mandatory_for_groups", [])

        # Filter candidate rooms by type, capacity, features, and allowed_uses
        candidate_rooms = []
        for r_id, r in self.rooms.items():
            if "event" not in r.get("allowed_uses", []):
                continue
            if req_types and r.get("type") not in req_types:
                continue
            if r.get("capacity", 0) < attendance:
                continue
            feats = set(r.get("features", [])) | ({"accessible"} if r.get("accessible") else set())
            if needs - feats:
                continue
            candidate_rooms.append(r)

        # Sort candidate rooms by capacity compactness (smallest sufficient first)
        candidate_rooms.sort(key=lambda r: r.get("capacity", 0))

        alternatives = []
        seen_placements = set()

        # Phase 1: Try candidate rooms in the requested windows
        for w in req.get("windows", []):
            day = w.get("day")
            from_p = w.get("from_period", 1)
            to_p = w.get("to_period", self.max_period)

            for room in candidate_rooms:
                rid = room["id"]
                # Scan start periods
                for sp in range(from_p, to_p - dur + 2):
                    ep = sp + dur - 1
                    if ep > self.max_period:
                        continue
                    key = (rid, day, sp, ep)
                    if key in seen_placements:
                        continue

                    # Validate hard availability
                    room_chk = self.availability_engine.check_room_availability(rid, day, sp, dur, ignore_booking_id=req.get("id"))
                    if not room_chk["available"]:
                        continue

                    if mand_groups:
                        grp_chk = self.availability_engine.check_mandatory_groups(mand_groups, day, sp, dur)
                        if not grp_chk["available"]:
                            continue

                    seen_placements.add(key)
                    alternatives.append({
                        "booking_id": req.get("id"),
                        "room_id": rid,
                        "room_name": room.get("name", rid),
                        "room_type": room.get("type"),
                        "day": day,
                        "start_period": sp,
                        "end_period": ep,
                        "capacity": room.get("capacity"),
                        "features": room.get("features", []),
                        "reason": f"Available in {rid} during window on {day} P{sp}-P{ep}",
                        "status": "offered"
                    })
                    if len(alternatives) >= max_suggestions:
                        return alternatives

        # Phase 2: If no window alternative found, scan other available days and slots
        for day in self.days:
            for sp in range(1, self.max_period - dur + 2):
                ep = sp + dur - 1
                for room in candidate_rooms:
                    rid = room["id"]
                    key = (rid, day, sp, ep)
                    if key in seen_placements:
                        continue

                    room_chk = self.availability_engine.check_room_availability(rid, day, sp, dur, ignore_booking_id=req.get("id"))
                    if not room_chk["available"]:
                        continue

                    if mand_groups:
                        grp_chk = self.availability_engine.check_mandatory_groups(mand_groups, day, sp, dur)
                        if not grp_chk["available"]:
                            continue

                    seen_placements.add(key)
                    alternatives.append({
                        "booking_id": req.get("id"),
                        "room_id": rid,
                        "room_name": room.get("name", rid),
                        "room_type": room.get("type"),
                        "day": day,
                        "start_period": sp,
                        "end_period": ep,
                        "capacity": room.get("capacity"),
                        "features": room.get("features", []),
                        "reason": f"Feasible alternative slot in {rid} on {day} P{sp}-P{ep}",
                        "status": "offered"
                    })
                    if len(alternatives) >= max_suggestions:
                        return alternatives

        return alternatives
