"""
Priority Engine for CIT Smart Venue Booking System.
Applies the official priority order and role category caps from Section 4 of the Problem Statement:
1. Exams
2. Regular classes (regular_session)
3. Institute events (institute_event)
4. Guest lectures (guest_lecture)
5. Department events (department_event)
6. Club events (club_event)
"""

from typing import List, Dict, Any, Optional

DEFAULT_PRIORITY_ORDER = [
    "exam",
    "regular_session",
    "institute_event",
    "guest_lecture",
    "department_event",
    "club_event"
]

DEFAULT_ROLE_CAP = {
    "admin": "institute_event",
    "faculty": "guest_lecture",
    "dept_coordinator": "department_event",
    "department_coordinator": "department_event",
    "club": "club_event",
    "club_rep": "club_event"
}

CATEGORY_WEIGHTS = {
    "institute_event": 5.0,
    "guest_lecture": 4.0,
    "department_event": 3.0,
    "club_event": 2.0
}


class BookingPriorityManager:
    """Manages booking priority hierarchies, role caps, and outranking checks."""

    def __init__(
        self,
        priority_order: Optional[List[str]] = None,
        role_category_cap: Optional[Dict[str, str]] = None
    ):
        self.priority_order = list(priority_order or DEFAULT_PRIORITY_ORDER)
        self.role_category_cap = dict(role_category_cap or DEFAULT_ROLE_CAP)
        self.version = 1

    def get_effective_category(self, req: Dict[str, Any]) -> str:
        """
        Calculates the effective category of a booking request.
        A user role cannot request a category higher than their permitted role cap.
        Matches exact validator logic:
          cap = role_category_cap.get(req["role"], "club_event")
          a = priority_order.index(requested_category)
          return priority_order[max(a, priority_order.index(cap))]
        """
        req_cat = req.get("requested_category", "club_event")
        role = req.get("role", "club")
        cap = self.role_category_cap.get(role, "club_event")

        order = self.priority_order
        a = order.index(req_cat) if req_cat in order else len(order) - 1
        cap_idx = order.index(cap) if cap in order else len(order) - 1
        eff_idx = max(a, cap_idx)
        return order[eff_idx]

    def outranks(self, r1: Dict[str, Any], r2: Dict[str, Any]) -> bool:
        """
        Returns True if request r1 has strict priority over request r2.
        Follows official tournament tie-breaking:
          1. Lower index in priority_order is higher priority.
          2. Tie-break: earlier submitted_at timestamp.
        """
        c1 = self.priority_order.index(self.get_effective_category(r1))
        c2 = self.priority_order.index(self.get_effective_category(r2))
        if c1 != c2:
            return c1 < c2
        return str(r1.get("submitted_at", "")) < str(r2.get("submitted_at", ""))

    def get_category_weight(self, category: str) -> float:
        return CATEGORY_WEIGHTS.get(category, 1.0)

    def update_config(self, new_order: List[str], new_caps: Optional[Dict[str, str]] = None):
        """Allows authorized admin update of priority configuration."""
        self.priority_order = list(new_order)
        if new_caps:
            self.role_category_cap.update(new_caps)
        self.version += 1
