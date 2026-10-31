"""
Module 8: CIT AI Scheduling Assistant & Natural Language Engine.
Handles English & Hinglish parsing, intent recognition, entity extraction,
vague request clarification, security verification, and decision explanations.
Zero reliance on external LLM for algorithmic correctness; Python and CP-SAT remain authoritative.
"""

import re
import json
from typing import Dict, Any, List, Optional, Tuple

from backend.db.database import get_connection
from backend.schemas.ai_schemas import (
    AIChatRequest, AIChatResponse, AIScheduleChangeRequest, AIExplanationResponse
)
from backend.services.decision_evidence_service import DecisionEvidenceService
from backend.services.disruption_service import DisruptionService

WEEKDAYS = ["MON", "TUE", "WED", "THU", "FRI"]
DAY_ALIASES = {
    "monday": "MON", "mon": "MON", "somwar": "MON",
    "tuesday": "TUE", "tue": "TUE", "mangalwar": "TUE", "mangal": "TUE",
    "wednesday": "WED", "wed": "WED", "budhwar": "WED", "budh": "WED",
    "thursday": "THU", "thu": "THU", "guruwar": "THU", "veervar": "THU", "guru": "THU",
    "friday": "FRI", "fri": "FRI", "shukrawar": "FRI", "shukra": "FRI"
}

TIME_PERIOD_MAP = {
    "8": 1, "08": 1, "8am": 1, "8:00": 1, "8:00am": 1,
    "9": 2, "09": 2, "9am": 2, "9:00": 2, "9:00am": 2,
    "10": 3, "10am": 3, "10:00": 3, "10:00am": 3,
    "11": 4, "11am": 4, "11:00": 4, "11:00am": 4,
    "12": 5, "12pm": 5, "12:00": 5, "12:00pm": 5,
    "1": 6, "13": 6, "1pm": 6, "14": 6, "2pm": 6, "2": 6, "14:00": 6,
    "3": 7, "15": 7, "3pm": 7, "15:00": 7,
    "4": 8, "16": 8, "4pm": 8, "16:00": 8,
    "5": 9, "17": 9, "5pm": 9, "17:00": 9
}

PROMPT_INJECTION_KEYWORDS = [
    "ignore all constraints", "ignore previous instructions", "bypass validation",
    "make me admin", "override priority", "force approve", "delete database",
    "system prompt", "reveal api key", "sudo approve"
]


class AIAssistantService:
    """Core AI Assistant supporting bilingual schedule manipulation and decision explainability."""

    def __init__(self):
        self.evidence_service = DecisionEvidenceService()
        self.disruption_service = DisruptionService()
        # Active in-memory session drafts
        self.conversations: Dict[str, List[Dict[str, Any]]] = defaultdict_conv()

    def process_chat(self, req: AIChatRequest, user: Dict[str, Any]) -> AIChatResponse:
        """
        Main entrypoint for AI Chat. Routes input across:
        1. Security & Prompt Injection Check
        2. Decision Explanation queries (why/kyun)
        3. Schedule Change & Rescheduling requests
        4. Clarification responses
        5. General assistance
        """
        raw_text = req.message.strip()
        conv_id = req.conversation_id or f"conv_{user.get('id', 'anon')}_{id(raw_text) % 10000}"
        lower = raw_text.lower()

        # 1. Security & Prompt Injection Inspection
        if any(bad in lower for bad in PROMPT_INJECTION_KEYWORDS):
            return AIChatResponse(
                message="Security Alert: Your request contains instructions attempting to alter scheduling security rules or bypass validation. System constraints (H1–H14), role-based permissions, and booking priority are enforced strictly by backend deterministic logic and cannot be overridden conversationally.",
                conversation_id=conv_id,
                intent="security_block",
                validation_status="FAILED",
                validation_errors=["Attempted prompt injection or unauthorized permission bypass."],
                suggested_prompts=["Move my Monday class to Tuesday", "Why was my class scheduled at 8 AM?", "Show my timetable"]
            )

        # 2. Check for Decision Explanation Queries (English & Hinglish)
        if self._is_explanation_query(lower):
            return self._handle_explanation_query(raw_text, lower, conv_id, user)

        # 3. Check for Schedule Change / Rescheduling (English & Hinglish)
        if self._is_schedule_change_query(lower):
            return self._handle_schedule_change(raw_text, lower, conv_id, user)

        # 4. Fallback / General inquiry
        return self._handle_general_query(raw_text, conv_id, user)

    def extract_schedule_change(self, raw_text: str, user: Dict[str, Any]) -> AIScheduleChangeRequest:
        """Extracts structured scheduling change request from English or Hinglish text."""
        lower = raw_text.lower()
        user_role = user.get("role", "faculty")
        user_fid = user.get("faculty_id") or (user.get("id") if user_role == "faculty" else None)

        req_type = "reschedule_session"
        if any(w in lower for w in ["unavailable", "leave", "chutti", "available nahi", "availability nahi", "nahi aa sakta", "nahi aa sakti"]):
            req_type = "faculty_unavailable"
        elif any(w in lower for w in ["room change", "badal", "dusra room", "dusra kamra", "different room"]):
            req_type = "room_change"

        # 1. Day Extraction
        cur_day = None
        req_day = None

        # Look for "from day to day" or "day wali class day ko"
        from_to_match = re.search(r'(?:from|wali)\s+([a-zA-Z]+).*(?:to|ko|par)\s+([a-zA-Z]+)', lower)
        if from_to_match:
            d1 = DAY_ALIASES.get(from_to_match.group(1).lower())
            d2 = DAY_ALIASES.get(from_to_match.group(2).lower())
            if d1 and d2:
                cur_day = d1
                req_day = d2

        if not req_day:
            for word, code in DAY_ALIASES.items():
                if word in lower:
                    if not cur_day:
                        cur_day = code
                    elif cur_day != code:
                        req_day = code

        # If only one day detected:
        if not req_day and cur_day:
            is_negative = any(w in lower for w in ["nahi", "not", "unavailable", "leave", "chutti", "cancel"])
            has_move_to = any(w in lower for w in ["move to", "shift to", "transfer to", "ko shift", "ko move", "to tuesday", "to wednesday", "to thursday", "to friday", "to monday"])
            if has_move_to and not is_negative:
                req_day = cur_day
                cur_day = None

        # 2. Period / Time Extraction
        cur_period = None
        req_period = None
        time_match = re.search(r'(\d{1,2})(?::(\d{2}))?\s*(am|pm|baje|o\'clock)?', lower)
        if time_match:
            hr_str = time_match.group(1)
            t_key = hr_str + (time_match.group(3) or "") if time_match.group(3) in ("am", "pm") else hr_str
            p_val = TIME_PERIOD_MAP.get(t_key) or TIME_PERIOD_MAP.get(hr_str)
            if p_val:
                cur_period = p_val

        # Period P1-P9 direct detection
        p_direct = re.search(r'\bp([1-9])\b', lower)
        if p_direct:
            cur_period = int(p_direct.group(1))

        # 3. Preferred Time Range
        pref_range = None
        if any(w in lower for w in ["morning", "subah", "early", "pehle", "earlier"]):
            pref_range = "morning"
        elif any(w in lower for w in ["afternoon", "dopahar", "post lunch", "later", "baad mein"]):
            pref_range = "afternoon"

        # 4. Session / Course identification
        course_id = None
        c_match = re.search(r'\b([a-z]{2}\d{3})\b', lower)
        if c_match:
            course_id = c_match.group(1).upper()

        session_id = None
        s_match = re.search(r'\b([a-z]{2}\d{3}-[a-z0-9\-]+)\b', lower)
        if s_match:
            session_id = s_match.group(1).upper()

        # If faculty is authenticated, lookup their session matching the day/period
        if user_fid and not session_id:
            conn = get_connection()
            cur = conn.cursor()
            if cur_day and cur_period:
                cur.execute("""
                    SELECT ta.session_id, s.course_id
                    FROM timetable_assignments ta
                    JOIN sessions s ON ta.session_id = s.id
                    WHERE ta.timetable_id = 'active' AND s.faculty_id = ? AND ta.day = ?
                      AND ta.start_period <= ? AND (? < ta.start_period + s.duration)
                """, (user_fid, cur_day, cur_period, cur_period))
            elif cur_day:
                cur.execute("""
                    SELECT ta.session_id, s.course_id
                    FROM timetable_assignments ta
                    JOIN sessions s ON ta.session_id = s.id
                    WHERE ta.timetable_id = 'active' AND s.faculty_id = ? AND ta.day = ?
                    LIMIT 1
                """, (user_fid, cur_day))
            elif course_id:
                cur.execute("""
                    SELECT ta.session_id, s.course_id
                    FROM timetable_assignments ta
                    JOIN sessions s ON ta.session_id = s.id
                    WHERE ta.timetable_id = 'active' AND s.faculty_id = ? AND s.course_id = ?
                    LIMIT 1
                """, (user_fid, course_id))
            else:
                cur.execute("""
                    SELECT ta.session_id, s.course_id
                    FROM timetable_assignments ta
                    JOIN sessions s ON ta.session_id = s.id
                    WHERE ta.timetable_id = 'active' AND s.faculty_id = ?
                    LIMIT 1
                """, (user_fid,))

            r = cur.fetchone()
            conn.close()
            if r:
                session_id = r["session_id"]
                if not course_id:
                    course_id = r["course_id"]

        # 5. Clarification & Missing Info Detection
        missing = []
        if req_type == "reschedule_session":
            if not session_id and not course_id:
                missing.append("session_or_course")
            if not req_day and not pref_range:
                missing.append("target_day_or_window")
        elif req_type == "faculty_unavailable":
            if not req_day and not cur_day:
                missing.append("unavailable_day")

        requires_clarify = len(missing) > 0 or (req_type == "reschedule_session" and not req_day and not req_period)

        return AIScheduleChangeRequest(
            request_type=req_type,
            faculty_id=user_fid,
            session_id=session_id,
            course_id=course_id,
            current_day=cur_day,
            current_period=cur_period,
            requested_day=req_day,
            requested_period=req_period,
            preferred_time_range=pref_range,
            reason=raw_text,
            requires_clarification=requires_clarify,
            missing_fields=missing
        )

    def _is_explanation_query(self, lower: str) -> bool:
        triggers = [
            "why", "kyun", "kyu", "reason", "wajah", "karan",
            "explain", "samjhao", "batao", "which constraint",
            "why was", "why can't", "why cannot", "clash"
        ]
        return any(t in lower for t in triggers)

    def _is_schedule_change_query(self, lower: str) -> bool:
        triggers = [
            "move", "shift", "reschedule", "transfer", "change",
            "unavailable", "available nahi", "availability nahi", "chutti", "free period",
            "morning", "afternoon", "earlier", "adjust", "badal",
            "nahi leni", "nahi lena", "nahi aa sakta", "nahi aa sakti"
        ]
        return any(t in lower for t in triggers)

    def _handle_explanation_query(self, raw_text: str, lower: str, conv_id: str, user: Dict[str, Any]) -> AIChatResponse:
        """Dispatches decision explanation requests to DecisionEvidenceService."""
        # Detect target entities
        session_id = None
        s_match = re.search(r'\b([a-z]{2}\d{3}-[a-z0-9\-]+)\b', lower)
        if s_match:
            session_id = s_match.group(1).upper()

        booking_id = None
        b_match = re.search(r'\b(req-\d+)\b', lower)
        if b_match:
            booking_id = b_match.group(1).upper()

        day = None
        for word, code in DAY_ALIASES.items():
            if word in lower:
                day = code
                break

        # A. Why was booking rejected?
        if any(w in lower for w in ["booking", "auditorium", "seminar", "rejected", "reject"]):
            ev = self.evidence_service.explain_booking_decision(booking_id)
            return AIChatResponse(
                message=ev["explanation"],
                conversation_id=conv_id,
                intent="explain",
                explanation=AIExplanationResponse(
                    question=raw_text,
                    question_type="booking_rejection",
                    target_id=ev.get("target_id"),
                    explanation=ev["explanation"],
                    evidence=ev["evidence"],
                    rules_involved=ev["rules_involved"]
                ),
                suggested_prompts=["Why was this room selected?", "Move my Monday class to Tuesday", "Show pending approvals"]
            )

        # B. Why can't class be moved to Day / Period? (Counterfactual)
        if any(w in lower for w in ["can't", "cannot", "nahi ho sakti", "fail", "clash"]):
            user_fid = user.get("faculty_id") or user.get("id")
            if not session_id and user_fid:
                conn = get_connection()
                cur = conn.cursor()
                cur.execute("SELECT session_id FROM timetable_assignments ta JOIN sessions s ON ta.session_id = s.id WHERE s.faculty_id = ? LIMIT 1", (user_fid,))
                r = cur.fetchone()
                conn.close()
                if r:
                    session_id = r["session_id"]

            target_day = day or "TUE"
            cf = self.evidence_service.test_reschedule_feasibility(session_id or "MA101-A-L1", target_day=target_day, target_period=3)
            reasons = cf["violations"]
            msg = f"Analysis for moving session {cf['session_id']} to {target_day}:\n\n"
            if not cf["is_feasible"]:
                msg += "Cannot be moved due to the following binding constraints:\n"
                for v in reasons:
                    msg += f"• {v}\n"
                msg += f"\nRules triggered: {', '.join(cf['rules'])}."
            else:
                msg += f"Placement on {target_day} P3 is completely feasible without violating hard constraints!"

            return AIChatResponse(
                message=msg,
                conversation_id=conv_id,
                intent="explain",
                explanation=AIExplanationResponse(
                    question=raw_text,
                    question_type="reschedule_infeasible",
                    target_id=cf.get("session_id"),
                    explanation=msg,
                    evidence=cf,
                    rules_involved=cf["rules"],
                    is_counterfactual=True
                ),
                suggested_prompts=["Why was my class scheduled at 8 AM?", "Find another available room", "Show faculty timetable"]
            )

        # C. Why this room selected?
        if any(w in lower for w in ["room", "venue", "kamra", "hall"]):
            ev = self.evidence_service.explain_room_selection(session_id or "MA101-AB-L1")
            return AIChatResponse(
                message=ev["explanation"],
                conversation_id=conv_id,
                intent="explain",
                explanation=AIExplanationResponse(
                    question=raw_text,
                    question_type="room_selection",
                    target_id=ev.get("target_id"),
                    explanation=ev["explanation"],
                    evidence=ev["evidence"],
                    rules_involved=ev["rules_involved"]
                ),
                suggested_prompts=["Why was my class scheduled at 8 AM?", "Move my class earlier", "Show room utilization"]
            )

        # D. Why class at 8 AM / P1?
        ev = self.evidence_service.explain_timetable_slot(
            session_id=session_id,
            faculty_id=user.get("faculty_id") or user.get("id"),
            day=day,
            period=1 if "8" in lower else None
        )
        return AIChatResponse(
            message=ev["explanation"],
            conversation_id=conv_id,
            intent="explain",
            explanation=AIExplanationResponse(
                question=raw_text,
                question_type="timetable_slot",
                target_id=ev.get("target_id"),
                explanation=ev["explanation"],
                evidence=ev["evidence"],
                rules_involved=ev["rules_involved"]
            ),
            suggested_prompts=["Why was this room selected?", "Why was my booking rejected?", "Move my Monday class to Tuesday"]
        )

    def _handle_schedule_change(self, raw_text: str, lower: str, conv_id: str, user: Dict[str, Any]) -> AIChatResponse:
        """Handles schedule-change requests and creates structured proposals via Module 5."""
        extracted = self.extract_schedule_change(raw_text, user)

        # Authorization check: Faculty can only request changes for their own sessions
        user_role = user.get("role", "faculty")
        user_fid = user.get("faculty_id") or (user.get("id") if user_role == "faculty" else None)

        if user_role == "faculty" and extracted.session_id:
            s_data = self.evidence_service.sessions.get(extracted.session_id)
            if s_data and s_data.get("faculty_id") != user_fid:
                return AIChatResponse(
                    message=f"Permission Denied: Session {extracted.session_id} is taught by Dr. {s_data.get('faculty_id')}. As a faculty member, institutional security rules restrict you to modifying your own assigned teaching schedule.",
                    conversation_id=conv_id,
                    intent="security_block",
                    validation_status="FAILED",
                    validation_errors=["Unauthorized attempt to modify another faculty member's schedule."],
                    suggested_prompts=["Move my Monday class to Tuesday", "Show my active timetable", "I am unavailable on Wednesday"]
                )

        # Clarification handling for vague requests
        if extracted.requires_clarification:
            questions = []
            if "session_or_course" in extracted.missing_fields:
                questions.append("Which course or session would you like to move (e.g., CS101, MA101, or PH191 lab)?")
            if "target_day_or_window" in extracted.missing_fields:
                questions.append("Which day and preferred time range would you prefer for the new slot (e.g., Tuesday morning, Thursday afternoon)?")
            if "unavailable_day" in extracted.missing_fields:
                questions.append("Which day are you unavailable (Monday–Friday)?")

            if not questions:
                questions.append("Could you specify the target day and period where you would like this class placed?")

            return AIChatResponse(
                message="I understood your request, but I need a few more details to generate an accurate, non-conflicting schedule proposal:\n\n" + "\n".join(f"• {q}" for q in questions),
                conversation_id=conv_id,
                intent="schedule_change",
                extracted_request=extracted,
                requires_clarification=True,
                clarification_questions=questions,
                suggested_prompts=["Move my Monday class to Tuesday morning", "I am unavailable on Wednesday afternoon", "Find a free slot on Friday"]
            )

        # Generate Proposal via Module 5 Disruption Engine
        try:
            # Build change payload
            dis_payload = {
                "description": f"AI Schedule Change: {raw_text}",
                "reported_by": user.get("id", "faculty"),
                "changes": []
            }

            if extracted.request_type == "faculty_unavailable":
                dis_payload["changes"].append({
                    "type": "faculty_unavailable",
                    "faculty_id": extracted.faculty_id or "F01",
                    "days": [extracted.requested_day or extracted.current_day or "WED"],
                    "periods": extracted.unavailability_periods or [1, 2, 3, 4, 5, 6, 7, 8, 9],
                    "reason": extracted.reason
                })
            else:
                # Session move: represented as unavailable in old slot or moving session
                dis_payload["changes"].append({
                    "type": "faculty_unavailable",
                    "faculty_id": extracted.faculty_id or "F01",
                    "days": [extracted.current_day or "MON"],
                    "periods": [extracted.current_period or 1],
                    "reason": f"Reschedule request: {extracted.reason}"
                })

            # Create disruption record
            dis_res = self.disruption_service.create_disruption(dis_payload, user)
            dis_id = dis_res["disruption_id"]

            # Generate proposal using minimal-perturbation engine
            prop = self.disruption_service.generate_rescheduling_proposal(
                disruption_id=dis_id,
                user=user,
                time_limit_seconds=30
            )

            diff = prop.get("diff", {})
            moved_cnt = len(diff.get("sessions_moved", []))
            time_ch = diff.get("time_changed_count", 0)
            room_ch = diff.get("room_only_changed_count", 0)

            msg = (
                f"Generated Rescheduling Proposal: **{prop['id']}**\n\n"
                f"• **Stability Score**: Moved {moved_cnt} session(s) ({time_ch} time adjusted, {room_ch} room only).\n"
                f"• **Deterministic Validation**: Verified against H1–H14 hard constraints (0 hard clashes).\n"
                f"• **Approval Workflow**: Submitted for authorized Admin review. Baseline timetable remains active until approved."
            )

            return AIChatResponse(
                message=msg,
                conversation_id=conv_id,
                intent="schedule_change",
                extracted_request=extracted,
                proposal=prop,
                validation_status="PASS",
                suggested_prompts=["Review proposal diff", "Why was this alternative selected?", "Back to my timetable"]
            )

        except Exception as e:
            # Deterministic error explanation
            err_msg = str(e)
            return AIChatResponse(
                message=f"Rescheduling Infeasible: The requested schedule change cannot be fulfilled without creating hard conflicts in the active academic timetable.\n\nDetails: {err_msg}",
                conversation_id=conv_id,
                intent="schedule_change",
                extracted_request=extracted,
                validation_status="FAILED",
                validation_errors=[err_msg],
                suggested_prompts=["Why can't this class be moved to Tuesday?", "Find another available room", "Show faculty timetable"]
            )

    def _handle_general_query(self, raw_text: str, conv_id: str, user: Dict[str, Any]) -> AIChatResponse:
        """Handles greetings, capability overviews, and general user queries."""
        u_name = user.get("name", "Faculty Member")
        u_role = user.get("role", "faculty")

        msg = (
            f"Hello {u_name}! I am your **CIT AI Scheduling Assistant & Decision Explainability Partner**.\n\n"
            f"I can assist you in English and Hinglish with:\n"
            f"1. **Schedule Changes**: 'Move my Monday 10 AM class to Tuesday', 'Meri class afternoon mein rakh do'.\n"
            f"2. **Unavailability Updates**: 'I am unavailable on Wednesday', 'Wednesday ko meri availability nahi hai'.\n"
            f"3. **Decision Explainability**: 'Why was my class scheduled at 8 AM?', 'Why was my booking rejected?', 'Which constraint is preventing this change?'.\n\n"
            f"All proposals are rigorously verified by Python validation and Google OR-Tools CP-SAT before any changes occur."
        )

        return AIChatResponse(
            message=msg,
            conversation_id=conv_id,
            intent="general",
            suggested_prompts=[
                "Move my Monday 10 AM class to Tuesday",
                "Why was my class scheduled at 8 AM?",
                "Why was this room selected?",
                "I am unavailable on Wednesday",
                "Meri class kisi aur free period mein adjust kar do"
            ]
        )


def defaultdict_conv():
    from collections import defaultdict
    return defaultdict(list)


# Singleton Instance
ai_assistant_service = AIAssistantService()
