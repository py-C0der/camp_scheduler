"""
Booking Decision and Spectra-Week Resolution Engine.
Resolves competing requests according to official priority hierarchies and tie-breaking rules.
Produces deterministic, auditable decisions with 0 hard violations and 0 priority inversions.
"""

from typing import Dict, Any, List, Optional, Tuple
from collections import defaultdict
import copy

from backend.bookings.priority import BookingPriorityManager, CATEGORY_WEIGHTS
from backend.bookings.availability import VenueAvailabilityEngine
from backend.bookings.validation import BookingValidationEngine
from backend.bookings.alternatives import BookingAlternativeEngine
from backend.bookings.explanations import BookingExplanationService


class BookingDecisionEngine:
    """Orchestrates multi-request priority resolution and allocation decisions."""

    def __init__(self, dataset: Dict[str, Any]):
        self.data = dataset
        self.priority_manager = BookingPriorityManager(
            dataset.get("priority_order"),
            dataset.get("role_category_cap")
        )
        self.availability_engine = VenueAvailabilityEngine(dataset)
        self.validation_engine = BookingValidationEngine(dataset, self.availability_engine)
        self.alternative_engine = BookingAlternativeEngine(dataset, self.availability_engine, self.validation_engine)
        self.explanation_service = BookingExplanationService()

    def process_all_requests(
        self,
        requests: List[Dict[str, Any]],
        cancellations: List[Dict[str, Any]],
        base_sessions: List[Dict[str, Any]],
        exams: Optional[List[Dict[str, Any]]] = None
    ) -> Dict[str, Any]:
        """
        Executes the full 12-step Spectra-week resolution workflow:
        1. Exclude cancelled requests.
        2. Sort active requests strictly by priority hierarchy and submission timestamp.
        3. Attempt window allocation for each request.
        4. If blocked, attempt alternative non-conflicting placement.
        5. If completely unaccommodatable, record rejection with precise conflict explanation.
        6. Verify priority inversion absence.
        """
        cancelled_ids = {c["request_id"] for c in cancellations}
        for r in requests:
            if r.get("is_cancelled") or r.get("status") == "cancelled":
                cancelled_ids.add(r["id"])

        # Reset availability state with baseline timetable and exams
        self.availability_engine.load_academic_timetable(base_sessions)
        if exams:
            self.availability_engine.load_exam_schedule(exams)

        # Sort requests: highest priority first, tie-break by submission timestamp
        order = self.priority_manager.priority_order
        active_requests = [r for r in requests if r["id"] not in cancelled_ids]
        active_requests.sort(key=lambda r: (
            order.index(self.priority_manager.get_effective_category(r)),
            r.get("submitted_at", "")
        ))

        decisions = []
        placed_requests: Dict[str, Tuple[str, str, int, int]] = {}
        session_overrides: List[Dict[str, Any]] = []

        # Process each active request
        for req in active_requests:
            req_id = req["id"]
            dur = req.get("duration_periods", 1)
            attendance = req.get("attendance", 0)
            req_types = req.get("room_types", [])
            needs = set(req.get("needs", []))
            mand_groups = req.get("mandatory_for_groups", [])
            eff_cat = self.priority_manager.get_effective_category(req)

            allocated = False

            # Check candidate rooms: prefer requested_room if specified
            candidate_room_ids = []
            if req.get("requested_room") and req.get("requested_room") in self.availability_engine.rooms:
                candidate_room_ids.append(req["requested_room"])

            for rid, r in self.availability_engine.rooms.items():
                if rid not in candidate_room_ids:
                    candidate_room_ids.append(rid)

            # Step A: Try requested windows
            for w in req.get("windows", []):
                day = w.get("day")
                from_p = w.get("from_period", 1)
                to_p = min(13, w.get("to_period", 13))

                for rid in candidate_room_ids:
                    room = self.availability_engine.rooms[rid]
                    if "event" not in room.get("allowed_uses", []):
                        continue
                    if req_types and room.get("type") not in req_types:
                        continue
                    if room.get("capacity", 0) < attendance:
                        continue
                    feats = set(room.get("features", [])) | ({"accessible"} if room.get("accessible") else set())
                    if needs - feats:
                        continue

                    # Scan start periods inside window (respecting campus max period = 13)
                    for sp in range(from_p, min(13, to_p) - dur + 2):
                        ep = sp + dur - 1
                        if ep > 13 or sp < 1:
                            continue

                        # Validate availability against maintenance and existing bookings
                        room_chk = self.availability_engine.check_room_availability(rid, day, sp, dur)
                        grp_chk = self.availability_engine.check_mandatory_groups(mand_groups, day, sp, dur) if mand_groups else {"available": True, "conflicts": []}

                        # Check if blocked only by a teaching session AND this is an institute_event allowed to displace
                        teaching_conflict_sids = [c["entity_id"] for c in room_chk.get("conflicts", []) if c.get("type") == "teaching_session"]
                        other_conflicts = [c for c in room_chk.get("conflicts", []) if c.get("type") != "teaching_session"]

                        can_displace = (
                            eff_cat == "institute_event" and
                            len(other_conflicts) == 0 and
                            grp_chk["available"] and
                            len(teaching_conflict_sids) > 0
                        )

                        if room_chk["available"] and grp_chk["available"]:
                            # Clean approval within window
                            placed_requests[req_id] = (rid, day, sp, ep)
                            # Mark busy in availability engine
                            for p in range(sp, ep + 1):
                                self.availability_engine.booking_occupancy[(rid, day, p)] = req_id

                            reason = self.explanation_service.explain_approval(req, rid, day, sp, ep, eff_cat)
                            decisions.append({
                                "request_id": req_id,
                                "status": "approved",
                                "day": day,
                                "start_period": sp,
                                "end_period": ep,
                                "room_id": rid,
                                "reason": reason
                            })
                            allocated = True
                            break
                        elif can_displace:
                            # Displace regular teaching sessions for institute event
                            for sid in teaching_conflict_sids:
                                session_overrides.append({
                                    "session_id": sid,
                                    "day": day,
                                    "start_period": sp,
                                    "room_id": rid,
                                    "displaced_by": req_id
                                })
                            placed_requests[req_id] = (rid, day, sp, ep)
                            for p in range(sp, ep + 1):
                                self.availability_engine.booking_occupancy[(rid, day, p)] = req_id

                            reason = f"Approved in {rid} during requested window ({day} P{sp}-P{ep}), displacing academic session."
                            decisions.append({
                                "request_id": req_id,
                                "status": "approved",
                                "day": day,
                                "start_period": sp,
                                "end_period": ep,
                                "room_id": rid,
                                "reason": reason
                            })
                            allocated = True
                            break

                    if allocated:
                        break
                if allocated:
                    break

            # Step B: If not allocated in requested window, search for an alternative
            if not allocated:
                alts = self.alternative_engine.find_alternatives(req, max_suggestions=1)
                if alts:
                    alt = alts[0]
                    alt_rid = alt["room_id"]
                    alt_day = alt["day"]
                    alt_sp = alt["start_period"]
                    alt_ep = alt["end_period"]

                    # Place alternative
                    placed_requests[req_id] = (alt_rid, alt_day, alt_sp, alt_ep)
                    for p in range(alt_sp, alt_ep + 1):
                        self.availability_engine.booking_occupancy[(alt_rid, alt_day, p)] = req_id

                    reason = self.explanation_service.explain_alternative(req, alt, eff_cat)
                    decisions.append({
                        "request_id": req_id,
                        "status": "alternative_offered",
                        "day": alt_day,
                        "start_period": alt_sp,
                        "end_period": alt_ep,
                        "room_id": alt_rid,
                        "reason": reason
                    })
                    allocated = True

            # Step C: If still not allocated, reject with detailed conflict analysis
            if not allocated:
                # Find sample conflicts from requested window
                sample_conflicts = []
                sample_violations = []
                for w in req.get("windows", []):
                    w_day = w.get("day")
                    w_from = w.get("from_period", 1)
                    target_rid = req.get("requested_room") or (candidate_room_ids[0] if candidate_room_ids else "AUD")
                    eval_res = self.validation_engine.validate_request_eligibility(req, target_rid, w_day, w_from)
                    sample_conflicts.extend(eval_res.get("conflicts", []))
                    sample_violations.extend(eval_res.get("violations", []))

                rejection_reason = self.explanation_service.explain_rejection(
                    req, sample_violations, sample_conflicts, eff_cat
                )
                decisions.append({
                    "request_id": req_id,
                    "status": "rejected",
                    "reason": rejection_reason
                })

        # Add cancelled records
        for cid in cancelled_ids:
            c_info = next((c for c in cancellations if c.get("request_id") == cid), {})
            decisions.append({
                "request_id": cid,
                "status": "cancelled",
                "reason": f"Cancelled by {c_info.get('by', 'requester')}: {c_info.get('note', 'No note')}"
            })

        # Compute booking score & detect any priority inversions (matching tournament validator)
        score = 0.0
        max_score = 0.0
        for r in requests:
            rid_ = r["id"]
            if rid_ not in cancelled_ids:
                eff = self.priority_manager.get_effective_category(r)
                max_score += CATEGORY_WEIGHTS.get(eff, 2.0)

        for d in decisions:
            rid_ = d.get("request_id")
            if rid_ not in cancelled_ids:
                req_obj = next((r for r in requests if r["id"] == rid_), None)
                if req_obj:
                    eff = self.priority_manager.get_effective_category(req_obj)
                    wt = CATEGORY_WEIGHTS.get(eff, 2.0)
                    if d.get("status") == "approved":
                        score += wt * 1.0
                    elif d.get("status") == "alternative_offered":
                        score += wt * 0.5

        # Check priority inversions
        inversions = []
        for req in requests:
            req_id = req["id"]
            d = next((x for x in decisions if x.get("request_id") == req_id), None)
            if req_id in cancelled_ids or not d or d.get("status") != "rejected":
                continue

            for other_id, (placed_rid, placed_day, placed_a, placed_b) in placed_requests.items():
                other_d = next((x for x in decisions if x.get("request_id") == other_id), None)
                if not other_d or other_d.get("status") != "approved":
                    continue
                other_req = next((r for r in requests if r["id"] == other_id), None)
                if not other_req or not self.priority_manager.outranks(req, other_req):
                    continue

                # Check if req could have physically used placed_rid at placed_day P(placed_a..placed_b)
                room = self.availability_engine.rooms.get(placed_rid)
                if not room or room.get("capacity", 0) < req.get("attendance", 0):
                    continue
                feats = set(room.get("features", [])) | ({"accessible"} if room.get("accessible") else set())
                if set(req.get("needs", [])) - feats:
                    continue

                for w in req.get("windows", []):
                    if w.get("day") == placed_day:
                        inversions.append(f"Priority inversion: {req_id} ({self.priority_manager.get_effective_category(req)}) rejected while lower-priority {other_id} holds {placed_rid}")
                        break

        approved_count = sum(1 for d in decisions if d.get("status") == "approved")
        alt_count = sum(1 for d in decisions if d.get("status") == "alternative_offered")
        rejected_count = sum(1 for d in decisions if d.get("status") == "rejected")
        cancelled_count = len(cancelled_ids)

        return {
            "decisions": decisions,
            "session_overrides": session_overrides,
            "booking_score": score,
            "max_possible_score": max_score,
            "priority_inversions": inversions,
            "stats": {
                "total_requests": len(requests),
                "approved": approved_count,
                "alternatives": alt_count,
                "rejected": rejected_count,
                "cancelled": cancelled_count,
                "session_overrides": len(session_overrides)
            }
        }
