"""
Notification Template Engine for CIT Campus Notifications.
Renders titles, messages, and email subjects dynamically based on event type and payload.
"""

from typing import Dict, Any, Tuple
from backend.notifications.events import EventTypes, NotificationEvent


class TemplateEngine:
    """
    Renders structured notification titles, body text, and email contents.
    """

    @staticmethod
    def render(event: NotificationEvent) -> Tuple[str, str, str, str]:
        """
        Returns: (title, message, email_subject, action_url)
        """
        p = event.payload or {}
        etype = event.event_type

        # Default fallbacks
        title = f"Campus Update: {etype.replace('_', ' ').title()}"
        msg = f"A new event of type {etype} has been recorded in the platform."
        action_url = "/#dashboard"

        # Module 2: Timetable
        if etype == EventTypes.TIMETABLE_APPROVED:
            ver = p.get("version", "Active")
            title = f"Academic Timetable Approved ({ver})"
            msg = f"The official campus academic timetable ({ver}) has been approved by Dean Academics. All 189 teaching sessions are locked and effective."
            action_url = "/#timetable"

        elif etype == EventTypes.TIMETABLE_UPDATED:
            ver = p.get("version", "Active")
            sessions = p.get("sessions_count", 189)
            title = f"Academic Timetable Updated ({ver})"
            msg = f"The semester timetable schedule was updated with {sessions} teaching sessions across all engineering cohorts."
            action_url = "/#timetable"

        elif etype == EventTypes.SESSION_RESCHEDULED:
            s_id = p.get("session_id", "Session")
            day = p.get("day", "")
            period = p.get("period", "")
            room = p.get("room", "")
            title = f"Teaching Session Rescheduled: {s_id}"
            msg = f"Session {s_id} has been moved to {day} at Period {period} in Room {room}."
            action_url = "/#timetable"

        # Module 3: Examinations
        elif etype == EventTypes.EXAM_SCHEDULE_APPROVED:
            ver = p.get("version", "exam_v1")
            approver = p.get("approved_by", "Dean Academics")
            title = f"Mid-Semester Examination Schedule Published ({ver})"
            msg = f"Official examination timetable {ver} was approved by {approver}. 41 exams scheduled across 10 exam windows with 50% room spacing enforced."
            action_url = "/#examinations"

        elif etype == EventTypes.EXAM_SCHEDULE_UPDATED:
            ver = p.get("version", "latest")
            penalty = p.get("soft_penalty", 0)
            title = f"Examination Timetable Solved ({ver})"
            msg = f"Constraint solver successfully generated examination schedule {ver} with soft penalty {penalty} and 0 hard conflicts."
            action_url = "/#examinations"

        # Module 4: Venue Bookings
        elif etype == EventTypes.BOOKING_SUBMITTED:
            b_id = event.related_record_id or p.get("booking_id", "BR")
            req_by = p.get("requester", "User")
            cat = p.get("category", "General")
            title = f"New Venue Booking Request: {b_id}"
            msg = f"Request {b_id} ({cat}) submitted by {req_by}. Awaiting priority arbitration and dean approval."
            action_url = f"/#bookings?id={b_id}"

        elif etype == EventTypes.BOOKING_APPROVED:
            b_id = event.related_record_id or p.get("booking_id", "BR")
            room = p.get("room_id", "Allocated Venue")
            day = p.get("day", "")
            periods = f"P{p.get('start_period', '')}-P{p.get('end_period', '')}"
            title = f"Booking Request Approved: {b_id}"
            msg = f"Your booking request {b_id} has been APPROVED for room {room} on {day} ({periods}). Reason: {p.get('reason', 'Valid request')}"
            action_url = f"/#bookings?id={b_id}"

        elif etype == EventTypes.BOOKING_REJECTED:
            b_id = event.related_record_id or p.get("booking_id", "BR")
            reason = p.get("reason", "Conflicted with higher priority session.")
            title = f"Booking Request Rejected: {b_id}"
            msg = f"Booking request {b_id} could not be approved. Decision rationale: {reason}"
            action_url = f"/#bookings?id={b_id}"

        elif etype == EventTypes.BOOKING_ALTERNATIVE_OFFERED:
            b_id = event.related_record_id or p.get("booking_id", "BR")
            alt_room = p.get("alternative_room", "")
            title = f"Alternative Venue Offered: {b_id}"
            msg = f"Requested room was unavailable for {b_id}. Alternative venue {alt_room} is suggested. Please review in the portal."
            action_url = f"/#bookings?id={b_id}"

        elif etype == EventTypes.BOOKING_CANCELLED:
            b_id = event.related_record_id or p.get("booking_id", "BR")
            title = f"Booking Cancelled: {b_id}"
            msg = f"Venue booking {b_id} has been cancelled. Released slots returned to campus pool."
            action_url = f"/#bookings?id={b_id}"

        # Module 5: Disruptions
        elif etype == EventTypes.DISRUPTION_REPORTED:
            d_id = event.related_record_id or p.get("disruption_id", "Disruption")
            desc = p.get("description", "Unplanned campus event reported.")
            title = f"Campus Disruption Reported: {d_id}"
            msg = f"Disruption logged: '{desc}'. Blast radius impact analysis is active."
            action_url = "/#disruptions"

        elif etype == EventTypes.RESCHEDULING_PROPOSED:
            prop_id = p.get("proposal_id", "Prop-1")
            moved = p.get("sessions_moved", 0)
            title = f"Rescheduling Proposal Generated ({prop_id})"
            msg = f"Minimal perturbation solver produced proposal {prop_id} moving {moved} sessions. Awaiting coordinator/admin sign-off."
            action_url = "/#disruptions"

        elif etype == EventTypes.RESCHEDULING_APPROVED:
            ver = p.get("version", "Active")
            moved = p.get("sessions_moved", 0)
            title = f"Disruption Rescheduling Applied ({ver})"
            msg = f"New schedule version {ver} is now ACTIVE. {moved} sessions moved to resolve all room and faculty disruptions."
            action_url = "/#disruptions"

        elif etype == EventTypes.RESCHEDULING_REJECTED:
            prop_id = p.get("proposal_id", "Prop-1")
            reason = p.get("reason", "Rejected by coordinator.")
            title = f"Rescheduling Proposal Rejected: {prop_id}"
            msg = f"Proposal {prop_id} was rejected ({reason}). Solver re-run required."
            action_url = "/#disruptions"

        # Approvals
        elif etype == EventTypes.APPROVAL_REQUIRED:
            rec_id = event.related_record_id or ""
            role_needed = p.get("role_required", "Admin")
            title = f"Action Required: Approval Needed for {rec_id}"
            msg = f"A new item ({rec_id}) is pending approval by {role_needed}."
            action_url = f"/#{event.related_module.replace('module_', '')}"

        elif etype == EventTypes.APPROVAL_COMPLETED:
            rec_id = event.related_record_id or ""
            by = p.get("approved_by", "Authorized User")
            title = f"Approval Completed: {rec_id}"
            msg = f"Item {rec_id} was formally approved by {by}."
            action_url = f"/#{event.related_module.replace('module_', '')}"

        email_subject = f"[CIT Campus Alert - {event.severity.upper()}] {title}"
        return title, msg, email_subject, action_url
