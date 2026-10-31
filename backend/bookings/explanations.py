"""
Explainability Service for Booking Decisions.
Generates crystal-clear, auditable explanations for approvals, rejections, and alternative offers.
"""

from typing import Dict, Any, List, Optional


class BookingExplanationService:
    """Generates detailed, rule-backed explanations for every decision outcome."""

    @staticmethod
    def explain_approval(
        req: Dict[str, Any],
        room_id: str,
        day: str,
        start_period: int,
        end_period: int,
        effective_category: str
    ) -> str:
        title = req.get("title") or req.get("id")
        return (
            f"Approved '{title}' ({effective_category}) in {room_id} on {day} "
            f"P{start_period}–P{end_period}. Satisfies capacity ({req.get('attendance')} attendees), "
            f"required features, and official priority hierarchy with 0 conflicts."
        )

    @staticmethod
    def explain_rejection(
        req: Dict[str, Any],
        violations: List[str],
        conflicts: List[Dict[str, Any]],
        effective_category: str
    ) -> str:
        title = req.get("title") or req.get("id")
        if not violations and not conflicts:
            return f"Rejected '{title}': Unable to find eligible venue or time window meeting all constraints."

        reasons = []
        for c in conflicts:
            c_type = c.get("type")
            day = c.get("day")
            p = c.get("period")
            entity = c.get("entity_id", "an existing event")
            if c_type == "teaching_session":
                reasons.append(f"conflicts with regular academic class {entity} on {day} P{p}")
            elif c_type == "exam":
                reasons.append(f"conflicts with mid-semester exam {entity} on {day} P{p}")
            elif c_type == "booking":
                reasons.append(f"conflicts with higher/equal priority booking {entity} on {day} P{p}")
            elif c_type == "maintenance":
                reasons.append(f"venue is undergoing scheduled maintenance on {day} P{p}")
            elif c_type == "group_class":
                reasons.append(f"mandatory student group has academic lecture {entity} on {day} P{p}")
            elif c_type == "group_exam":
                reasons.append(f"mandatory student group is taking mid-sem exam {entity} on {day} P{p}")

        for v in violations:
            if "capacity" in v.lower():
                reasons.append("requested attendance exceeds venue capacity")
            elif "lacks" in v.lower():
                reasons.append("requested equipment or room features are unavailable")
            elif "cancelled" in v.lower():
                reasons.append("booking was formally cancelled by requester")
            elif "not authorized" in v.lower():
                reasons.append("venue cannot be used for events")

        detail_str = "; ".join(dict.fromkeys(reasons)) if reasons else "; ".join(violations[:2])
        return f"Rejected '{title}' ({effective_category}): {detail_str}."

    @staticmethod
    def explain_alternative(
        req: Dict[str, Any],
        alt: Dict[str, Any],
        effective_category: str
    ) -> str:
        title = req.get("title") or req.get("id")
        rid = alt.get("room_id")
        day = alt.get("day")
        sp = alt.get("start_period")
        ep = alt.get("end_period")
        return (
            f"Alternative offered for '{title}' ({effective_category}) in {rid} on {day} "
            f"P{sp}–P{ep}. Requested slot was occupied or unavailable; alternative satisfies capacity "
            f"({alt.get('capacity')} seats) and required equipment without clashes."
        )
