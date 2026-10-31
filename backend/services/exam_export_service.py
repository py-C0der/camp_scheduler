from __future__ import annotations

import json
from pathlib import Path
from typing import Any
from backend.config import EXPORTS_DIR

SCHEDULE_JSON_PATH = EXPORTS_DIR / "schedule.json"
EXAMS_JSON_PATH = EXPORTS_DIR / "exams.json"


class ExamExportService:
    """Manages official export formatting and synchronization for examinations."""

    @staticmethod
    def format_official_exams(assignments: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Transforms internal assignments into the exact official JSON structure."""
        formatted = []
        for a in assignments:
            formatted.append({
                "exam_id": a["exam_id"],
                "day": a["day"],
                "session": a["session"],
                "rooms": sorted(a.get("rooms", [])),
            })
        return formatted

    @classmethod
    def sync_to_schedule_export(cls, assignments: list[dict[str, Any]]) -> dict[str, Any]:
        """Updates the 'exams' section of exports/schedule.json preserving sessions & fest_week."""
        EXPORTS_DIR.mkdir(parents=True, exist_ok=True)
        official_exams = cls.format_official_exams(assignments)

        schedule_data = {}
        if SCHEDULE_JSON_PATH.exists():
            try:
                with SCHEDULE_JSON_PATH.open("r", encoding="utf-8") as f:
                    schedule_data = json.load(f)
            except Exception:
                schedule_data = {}

        if not schedule_data:
            schedule_data = {
                "team": "Team IIT BBS",
                "dataset_id": "cit-public-v1",
                "sessions": [],
                "fest_week": {"bookings": [], "session_overrides": []},
            }

        schedule_data["exams"] = official_exams

        with SCHEDULE_JSON_PATH.open("w", encoding="utf-8") as f:
            json.dump(schedule_data, f, indent=2)

        # Also write standalone exams.json for dedicated export downloads
        with EXAMS_JSON_PATH.open("w", encoding="utf-8") as f:
            json.dump(official_exams, f, indent=2)

        return {
            "status": "SAVED",
            "schedule_path": str(SCHEDULE_JSON_PATH),
            "exams_path": str(EXAMS_JSON_PATH),
            "exam_count": len(official_exams),
        }
