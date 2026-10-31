"""
Official Booking Export Service.
Generates tournament-compliant booking payloads for exports/schedule.json and exports/bookings.json.
Follows the exact JSON structure defined in the CrunchWeek starter-pack and official validator.
"""

import json
from pathlib import Path
from typing import Dict, Any, List, Optional
from backend.db.database import get_connection

SCHEDULE_PATH = Path(__file__).resolve().parent.parent.parent / "exports" / "schedule.json"
BOOKINGS_PATH = Path(__file__).resolve().parent.parent.parent / "exports" / "bookings.json"


class BookingExportService:
    """Synchronizes booking decisions with official schedule exports."""

    @classmethod
    def export_booking_decisions(
        cls,
        decisions: Optional[List[Dict[str, Any]]] = None,
        session_overrides: Optional[List[Dict[str, Any]]] = None
    ) -> Dict[str, Any]:
        """
        Reads decisions and overrides from database or parameters,
        updates exports/schedule.json, and writes standalone exports/bookings.json.
        """
        if decisions is None:
            conn = get_connection()
            cur = conn.cursor()
            cur.execute("""
                SELECT id, status, assigned_room_id, assigned_day, assigned_start_period,
                       assigned_end_period, decision_reason, is_cancelled, cancellation_note
                FROM booking_requests
                ORDER BY id ASC
            """)
            rows = cur.fetchall()
            decisions = []
            for r in rows:
                req_id = r["id"]
                st = r["status"]
                item = {
                    "request_id": req_id,
                    "status": st,
                    "reason": r["decision_reason"] or "Processed according to priority rules"
                }
                if st in ("approved", "alternative_offered") and r["assigned_room_id"]:
                    item["day"] = r["assigned_day"]
                    item["start_period"] = r["assigned_start_period"]
                    item["end_period"] = r["assigned_end_period"]
                    item["room_id"] = r["assigned_room_id"]
                decisions.append(item)

            # Read fest overrides
            cur.execute("SELECT session_id, day, start_period, room_id, displaced_by FROM fest_overrides")
            orows = cur.fetchall()
            session_overrides = [
                {
                    "session_id": o["session_id"],
                    "day": o["day"],
                    "start_period": o["start_period"],
                    "room_id": o["room_id"],
                    "displaced_by": o["displaced_by"]
                }
                for o in orows
            ]
            conn.close()

        session_overrides = session_overrides or []

        # 1. Update exports/schedule.json
        schedule_data = {}
        if SCHEDULE_PATH.exists():
            try:
                with open(SCHEDULE_PATH, "r", encoding="utf-8") as f:
                    schedule_data = json.load(f)
            except Exception:
                schedule_data = {}

        schedule_data.setdefault("team", "CIT-DevOps")
        schedule_data.setdefault("dataset_id", "cit-public-v1")
        schedule_data["fest_week"] = {
            "bookings": decisions,
            "session_overrides": session_overrides
        }

        SCHEDULE_PATH.parent.mkdir(parents=True, exist_ok=True)
        with open(SCHEDULE_PATH, "w", encoding="utf-8") as f:
            json.dump(schedule_data, f, indent=2)

        # 2. Write standalone exports/bookings.json
        booking_export_payload = {
            "team": "CIT-DevOps",
            "dataset_id": schedule_data.get("dataset_id", "cit-public-v1"),
            "fest_week": {
                "bookings": decisions,
                "session_overrides": session_overrides
            }
        }
        with open(BOOKINGS_PATH, "w", encoding="utf-8") as f:
            json.dump(booking_export_payload, f, indent=2)

        return booking_export_payload
