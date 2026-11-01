"""
CSV Dataset Ingestion and Conversion Helper for CIT Campus Management Platform.
Reads all CSV files from CrunchWeek_StarterPack/data/csv/ and converts them
into the unified dictionary format expected by DatasetService and cit_public.json.
"""

import csv
import json
import ast
import io
from pathlib import Path
from typing import Dict, Any, Optional, List

DEFAULT_CSV_DIR = Path(__file__).resolve().parent.parent.parent / "CrunchWeek_StarterPack" / "data" / "csv"

def parse_csv_value(v: Any) -> Any:
    if v is None:
        return None
    val_str = str(v).strip()
    if val_str == "" or val_str.lower() in ["null", "none"]:
        return None
    if val_str.lower() == "true":
        return True
    if val_str.lower() == "false":
        return False
    if (val_str.startswith("[") and val_str.endswith("]")) or (val_str.startswith("{") and val_str.endswith("}")):
        try:
            return json.loads(val_str)
        except Exception:
            try:
                return ast.literal_eval(val_str)
            except Exception:
                return val_str
    try:
        if "." in val_str:
            return float(val_str)
        return int(val_str)
    except Exception:
        return val_str

def parse_single_csv_string(csv_text: str, table_hint: str = "") -> List[Dict[str, Any]]:
    """
    Parses a single CSV text string into a list of typed dicts.
    Robustly handles UTF-8 BOM, UTF-16 BOM, CRLF/LF line endings,
    auto-detected delimiters (comma, semicolon, tab, pipe),
    and normalizes primary key aliases (course_id, faculty_id, room_id, etc.).
    """
    if not csv_text:
        return []
    
    # Strip any BOM characters and null bytes
    csv_text = str(csv_text).replace("\ufeff", "").replace("\ufffe", "").strip()
    if not csv_text:
        return []

    lines = [l for l in csv_text.splitlines() if l.strip()]
    if not lines:
        return []

    # Auto-detect delimiter from the header line
    first_line = lines[0]
    best_delim = ','
    max_count = 0
    for d in [',', ';', '\t', '|']:
        cnt = first_line.count(d)
        if cnt > max_count:
            max_count = cnt
            best_delim = d

    reader = csv.DictReader(io.StringIO(csv_text), delimiter=best_delim)
    items = []
    for row in reader:
        cleaned_row = {}
        for k, v in row.items():
            if k is not None:
                clean_k = str(k).strip().replace("\ufeff", "").replace("\ufffe", "").strip('"').strip("'").strip()
                cleaned_row[clean_k] = parse_csv_value(v)

        # Primary key normalization to 'id'
        if "id" not in cleaned_row or not cleaned_row["id"]:
            for alt in [
                "course_id", "faculty_id", "room_id", "group_id", "student_group_id",
                "session_id", "request_id", "code", "Course ID", "Room ID", "Faculty ID",
                "COURSE_ID", "FACULTY_ID", "ROOM_ID", "ID"
            ]:
                if alt in cleaned_row and cleaned_row[alt]:
                    cleaned_row["id"] = cleaned_row[alt]
                    break

        # Exam ID normalization
        if "exam_id" not in cleaned_row or not cleaned_row["exam_id"]:
            if "id" in cleaned_row and cleaned_row["id"]:
                cleaned_row["exam_id"] = cleaned_row["id"]

        # Booking request normalization
        if "request_id" not in cleaned_row or not cleaned_row["request_id"]:
            if "id" in cleaned_row and cleaned_row["id"]:
                cleaned_row["request_id"] = cleaned_row["id"]

        items.append(cleaned_row)
    return items

def parse_csv_directory(csv_dir: Optional[Path] = None) -> Dict[str, Any]:
    """
    Parses all CSV spreadsheets from directory into full CIT dataset structure.
    """
    if csv_dir is None:
        csv_dir = DEFAULT_CSV_DIR

    if not csv_dir.exists():
        raise FileNotFoundError(f"CSV directory not found: {csv_dir}")

    data: Dict[str, Any] = {
        "dataset_id": "cit-public-csv-v1",
        "institute": "Chilika Institute of Technology",
        "academic_year": "2026-2027",
        "semester": "Autumn",
        "calendar": {
            "days": ["MON", "TUE", "WED", "THU", "FRI"],
            "teaching_periods": [1, 2, 3, 4, 5, 6, 7, 8, 9],
            "event_periods": [10, 11, 12, 13],
            "period_times": {
                "1": "08:00-09:00",
                "2": "09:00-10:00",
                "3": "10:00-11:00",
                "4": "11:00-12:00",
                "5": "12:00-13:00",
                "lunch": "13:00-14:00",
                "6": "14:00-15:00",
                "7": "15:00-16:00",
                "8": "16:00-17:00",
                "9": "17:00-18:00",
                "10": "18:00-19:00",
                "11": "19:00-20:00",
                "12": "20:00-21:00",
                "13": "21:00-22:00"
            },
            "exam_week": {
                "days": ["MON", "TUE", "WED", "THU", "FRI", "SAT"],
                "sessions": {
                    "AM": "09:30-11:30",
                    "PM": "14:00-16:00"
                }
            }
        },
        "priority_order": [
            "midsem_exam",
            "class",
            "institute_event",
            "guest_lecture",
            "dept_event",
            "club_event"
        ],
        "role_category_cap": {
            "admin": "institute_event",
            "department_coordinator": "dept_event",
            "faculty": "guest_lecture",
            "club": "club_event"
        }
    }

    alias_map = {
        "courses": "courses", "course": "courses",
        "rooms": "rooms", "room": "rooms",
        "faculty": "faculty", "faculties": "faculty",
        "sessions": "sessions", "session": "sessions",
        "student_groups": "student_groups", "student_group": "student_groups", "groups": "student_groups",
        "exams": "exams", "exam": "exams",
        "booking_requests": "booking_requests", "bookings": "booking_requests",
        "room_unavailability": "room_unavailability", "unavailability": "room_unavailability",
        "cancellations": "cancellations"
    }

    for f in csv_dir.glob("*.csv"):
        raw_key = f.stem.lower()
        key = alias_map.get(raw_key, raw_key)
        with open(f, "r", encoding="utf-8-sig") as fp:
            raw_text = fp.read()
            items = parse_single_csv_string(raw_text, table_hint=key)
            data[key] = items

    # Map room_unavailability into rooms
    if "room_unavailability" in data and "rooms" in data:
        room_map = {r["id"]: r for r in data["rooms"] if "id" in r}
        for un in data["room_unavailability"]:
            rid = un.get("room_id")
            if rid in room_map:
                if "unavailable" not in room_map[rid]:
                    room_map[rid]["unavailable"] = []
                room_map[rid]["unavailable"].append({
                    "day": un.get("day"),
                    "periods": un.get("periods", []),
                    "reason": un.get("reason", "Maintenance")
                })

    return data


