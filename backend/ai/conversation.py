"""
Multi-turn Conversation and Clarification Engine.
Analyzes extracted booking details, detects missing or contradictory fields,
and generates polite, targeted follow-up questions.
"""

from typing import Dict, Any, List, Optional


class BookingClarificationAssistant:
    """Detects ambiguities and inconsistencies in booking requests."""

    @classmethod
    def analyze_booking_draft(cls, extracted: Dict[str, Any], raw_text: str) -> Dict[str, Any]:
        """
        Validates extraction completeness and returns:
        - is_complete (bool)
        - missing_fields (list)
        - clarification_questions (list)
        - contradictions (list)
        """
        missing_fields = []
        questions = []
        contradictions = []

        # 1. Check Date / Day
        if not extracted.get("detected_day"):
            missing_fields.append("day")
            questions.append("Which day would you like to schedule the event (e.g., Monday, Thursday, Friday)?")

        # 2. Check Timing / Window
        windows = extracted.get("windows", [])
        if not windows:
            missing_fields.append("time_window")
            questions.append("What time or periods would you prefer (e.g., 10 AM to 1 PM, or morning/afternoon)?")
        else:
            w = windows[0]
            from_p = w.get("from_period", 1)
            to_p = w.get("to_period", 1)
            dur = extracted.get("duration_periods", 1)

            if from_p > to_p:
                contradictions.append(f"Contradictory time: Start period P{from_p} occurs after end period P{to_p}.")
            if dur > (to_p - from_p + 1):
                contradictions.append(f"Inconsistent timing: Requested duration ({dur} periods) exceeds the window range (P{from_p}–P{to_p}).")

        # 3. Check Duration
        dur = extracted.get("duration_periods", 0)
        if dur <= 0:
            missing_fields.append("duration")
            questions.append("How many hours or periods will the event last?")
        elif dur > 10:
            contradictions.append(f"Unsupported duration: {dur} continuous periods exceeds campus operating rules.")

        # 4. Check Attendance
        attendance = extracted.get("attendance", 0)
        if attendance <= 0:
            contradictions.append("Invalid attendance: Expected attendee count cannot be negative or zero.")
        elif attendance < 5 and "around" not in raw_text.lower():
            # Might be ambiguous attendance
            missing_fields.append("attendance")
            questions.append("How many participants or students are expected to attend?")

        # 5. Check Room Types
        room_types = extracted.get("room_types", [])
        if not room_types:
            missing_fields.append("room_type")
            questions.append("What type of venue do you need (e.g., auditorium, computer lab, seminar hall, classroom)?")

        # 6. Event Name / Title
        title = extracted.get("title", "")
        if not title or title == "Campus Event":
            questions.append("What is the official title or topic of this event?")

        is_complete = len(missing_fields) == 0 and len(contradictions) == 0

        return {
            "is_complete": is_complete,
            "missing_fields": missing_fields,
            "clarification_questions": questions,
            "contradictions": contradictions
        }
