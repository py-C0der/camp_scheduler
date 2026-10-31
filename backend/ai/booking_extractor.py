"""
Natural Language Booking Extractor.
Processes plain English, Hinglish, and conversational campus venue booking requests.
Converts unstructured messages into structured, editable booking drafts.
Includes deterministic NLP rules ensuring 100% functionality without LLM API keys.
"""

import re
import os
import json
from datetime import datetime
from typing import Dict, Any, List, Optional, Tuple

# Day mappings
DAY_PATTERNS = {
    "MON": [r"\bmonday\b", r"\bmon\b", r"\bsomwar\b", r"\bsomvaar\b"],
    "TUE": [r"\btuesday\b", r"\btue\b", r"\bmangalwar\b", r"\bmangalvaar\b"],
    "WED": [r"\bwednesday\b", r"\bwed\b", r"\bbudhwar\b", r"\bbudhvaar\b"],
    "THU": [r"\bthursday\b", r"\bthu\b", r"\bguruwar\b", r"\bguruvaar\b", r"\bbrihaspati\b"],
    "FRI": [r"\bfriday\b", r"\bfri\b", r"\bshukrawar\b", r"\bshukravaar\b"],
    "SAT": [r"\bsaturday\b", r"\bsat\b", r"\bshaniwar\b", r"\bshanivaar\b"]
}

# Room type mappings
ROOM_TYPE_PATTERNS = {
    "auditorium": [r"\bauditorium\b", r"\baudi\b", r"\bmain hall\b"],
    "seminar_hall": [r"\bseminar hall\b", r"\bseminar\b", r"\bsh-1\b", r"\bsh-2\b", r"\bsh1\b", r"\bsh2\b"],
    "lecture_hall": [r"\blecture hall\b", r"\blh\b", r"\blh-", r"\blh1\b", r"\blh2\b"],
    "classroom": [r"\bclassroom\b", r"\bclass room\b", r"\bcr-", r"\bcr101\b", r"\bcr201\b", r"\bclass\b"],
    "lab_cs": [r"\bcomputer lab\b", r"\bcs lab\b", r"\bcoding lab\b", r"\blab_cs\b", r"\bpc lab\b"],
    "open_air_theatre": [r"\bopen air theatre\b", r"\bopen air theater\b", r"\boat\b", r"\bamphitheatre\b"]
}

# Needs / Equipment mappings
EQUIPMENT_PATTERNS = {
    "projector": [r"\bprojector\b", r"\bscreen\b", r"\bdisplay\b"],
    "computers": [r"\bcomputers\b", r"\bcomputer\b", r"\bpcs\b", r"\blaptops\b", r"\bsystems\b"],
    "pa_system": [r"\bpa system\b", r"\bsound system\b", r"\bsound\b", r"\baudio\b", r"\bmic\b", r"\bmicrophone\b", r"\bspeakers\b"],
    "stage": [r"\bstage\b", r"\bpodium\b"]
}

# Category inference mappings
CATEGORY_PATTERNS = {
    "institute_event": [r"\binauguration\b", r"\bvaledictory\b", r"\bfoundation day\b", r"\bconvocation\b", r"\bfest inauguration\b", r"\bofficial ceremony\b"],
    "guest_lecture": [r"\bguest lecture\b", r"\bkeynote\b", r"\btalk\b", r"\bdistinguished speaker\b", r"\binvited talk\b", r"\bscientist\b"],
    "department_event": [r"\bdepartment\b", r"\bdept meeting\b", r"\bfaculty meeting\b", r"\bboard meeting\b", r"\bdepartment workshop\b"],
    "club_event": [r"\bhackathon\b", r"\bcompetition\b", r"\bclub\b", r"\bworkshop\b", r"\bsprint\b", r"\brobotics\b", r"\bcoding\b", r"\bcultural\b"]
}


class NaturalLanguageBookingExtractor:
    """Extracts structured fields from plain English and Hinglish messages."""

    @classmethod
    def extract_fields(cls, text: str, user_role: str = "club") -> Dict[str, Any]:
        """
        Parses text and returns a dictionary of extracted booking fields.
        """
        lower = text.lower()

        # 1. Day Extraction
        detected_day = None
        for day, patterns in DAY_PATTERNS.items():
            for pat in patterns:
                if re.search(pat, lower):
                    detected_day = day
                    break
            if detected_day:
                break

        # Check relative days: kal (tomorrow -> assume TUE if MON, etc.)
        if not detected_day:
            if re.search(r"\bkal\b|\btomorrow\b", lower):
                detected_day = "TUE"  # Standard demonstration mapping
            elif re.search(r"\baaj\b|\btoday\b", lower):
                detected_day = "MON"

        # 2. Attendance Extraction
        attendance = 50  # default sensible estimate
        att_match = re.search(r"(\d+)\s*(?:students|participants|people|attendees|candidates|around|approx|persons)", lower)
        if att_match:
            attendance = int(att_match.group(1))
        else:
            # Fallback check numbers
            num_matches = re.findall(r"\b(\d{2,4})\b", lower)
            if num_matches:
                attendance = int(num_matches[0])

        # 3. Room Type Extraction
        detected_room_types = []
        for rtype, patterns in ROOM_TYPE_PATTERNS.items():
            for pat in patterns:
                if re.search(pat, lower):
                    detected_room_types.append(rtype)
                    break

        if not detected_room_types:
            # Default room type based on attendance or keywords
            if attendance >= 250:
                detected_room_types = ["auditorium"]
            elif attendance >= 80:
                detected_room_types = ["seminar_hall", "lecture_hall"]
            else:
                detected_room_types = ["classroom"]

        # Check explicit room mention
        requested_room = None
        if re.search(r"\baud\b|\bauditorium\b", lower):
            requested_room = "AUD"
        elif re.search(r"\boat\b", lower):
            requested_room = "OAT"
        elif re.search(r"\bsh-1\b|\bsh1\b", lower):
            requested_room = "SH-1"
        elif re.search(r"\bsh-2\b|\bsh2\b", lower):
            requested_room = "SH-2"
        elif re.search(r"\blh-1\b|\blh1\b", lower):
            requested_room = "LH-1"
        elif re.search(r"\blab-cs1\b|\blabcs1\b", lower):
            requested_room = "LAB-CS1"

        # 4. Equipment & Needs
        needs = []
        for eq, patterns in EQUIPMENT_PATTERNS.items():
            for pat in patterns:
                if re.search(pat, lower):
                    needs.append(eq)
                    break

        # 5. Timing and Duration Extraction
        # Look for duration: e.g. "6 straight hours", "2 hours", "3 hrs"
        duration_periods = 2
        dur_match = re.search(r"(\d+)\s*(?:hours|hour|hrs|hr|periods|straight hours)", lower)
        if dur_match:
            duration_periods = int(dur_match.group(1))

        # Look for time intervals: e.g., "10 AM to 1 PM", "2 pm and 10 pm", "morning", "afternoon"
        from_period = 3  # 10:30 default
        to_period = 6

        # Convert clock hours to periods
        # Periods: P1=8:30, P2=9:30, P3=10:30, P4=11:30, Lunch=12:30..13:30, P5=13:30, P6=14:30, P7=15:30, P8=16:30, P9=17:30, P10=18:30, P11=19:30, P12=20:30, P13=21:30
        clock_match = re.search(r"(\d{1,2})(?::\d{2})?\s*(am|pm)?\s*(?:to|and|-)\s*(\d{1,2})(?::\d{2})?\s*(am|pm)", lower)
        if clock_match:
            h1 = int(clock_match.group(1))
            m1 = clock_match.group(2) or "am"
            h2 = int(clock_match.group(3))
            m2 = clock_match.group(4) or "pm"

            # Normalize to 24h
            if m1 == "pm" and h1 < 12:
                h1 += 12
            if m1 == "am" and h1 == 12:
                h1 = 0
            if m2 == "pm" and h2 < 12:
                h2 += 12
            if m2 == "am" and h2 == 12:
                h2 = 0

            # Approximate period mapping
            from_period = max(1, min(13, h1 - 8))
            to_period = max(from_period, min(13, h2 - 9))
            duration_periods = max(1, to_period - from_period + 1)
        elif re.search(r"\bafternoon\b|\bdopahar\b", lower):
            from_period = 6  # 14:30
            to_period = 9    # 17:30
            duration_periods = min(duration_periods, 2)
        elif re.search(r"\bmorning\b|\bsubah\b", lower):
            from_period = 2  # 09:30
            to_period = 5    # 12:30
            duration_periods = min(duration_periods, 2)

        # 6. Category Extraction
        detected_category = "club_event"
        for cat, patterns in CATEGORY_PATTERNS.items():
            for pat in patterns:
                if re.search(pat, lower):
                    detected_category = cat
                    break
            if detected_category != "club_event":
                break

        # Adjust category by user role if restricted
        if user_role == "club" and detected_category not in ["club_event"]:
            detected_category = "club_event"

        # 7. Event Name / Title extraction
        # Try finding after 'for' or before 'on'
        title = "Campus Event"
        title_patterns = [
            r"for\s+([a-zA-Z0-9\s\'-]+?)(?:\s+on|\s+from|\s+for|\s+around|$)",
            r"chahiye[,\s]+([a-zA-Z0-9\s\'-]+?)(?:\s+ke liye|\s+around|$)",
            r"for\s+([a-zA-Z0-9\s\'-]+)",
            r"book\s+([a-zA-Z0-9\s\'-]+)"
        ]
        for tp in title_patterns:
            m = re.search(tp, text, re.IGNORECASE)
            if m and len(m.group(1).strip()) > 3:
                candidate = m.group(1).strip()
                # Clean up filler words
                candidate = re.sub(r"\b(robotics|competition|hackathon|seminar|meeting|guest lecture|talk)\b", r"\1", candidate, flags=re.I)
                title = candidate.title()
                break

        if title == "Campus Event":
            if "hackathon" in lower:
                title = "Coding Hackathon"
            elif "robotics" in lower:
                title = "Robotics Competition"
            elif "guest lecture" in lower or "talk" in lower:
                title = "Distinguished Guest Lecture"
            elif "meeting" in lower:
                title = "Department Meeting"

        # Construct single or multi-window definition
        day_str = detected_day or "FRI"
        windows = [{
            "day": day_str,
            "from_period": from_period,
            "to_period": max(from_period + duration_periods - 1, to_period)
        }]

        return {
            "title": title,
            "requested_category": detected_category,
            "attendance": attendance,
            "duration_periods": duration_periods,
            "room_types": detected_room_types,
            "windows": windows,
            "needs": needs,
            "mandatory_for_groups": [],
            "requested_room": requested_room,
            "detected_day": detected_day,
            "raw_text": text
        }
