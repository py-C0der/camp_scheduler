"""
Booking Dataset Ingestion Service.
Loads all booking requests and cancellations dynamically from cit_public.json.
Preserves original IDs and metadata without hard-coding counts.
"""

import json
from pathlib import Path
from typing import Dict, Any, List, Optional
from backend.db.database import get_connection
from backend.bookings.priority import BookingPriorityManager

DATASET_PATH = Path(__file__).resolve().parent.parent.parent / "CrunchWeek_StarterPack" / "data" / "cit_public.json"


class BookingIngestionService:
    """Dynamically loads and validates campus booking requests and cancellations."""

    def __init__(self, data_path: Optional[Path] = None):
        self.data_path = data_path or DATASET_PATH
        self.raw_data: Dict[str, Any] = {}
        self.priority_manager = BookingPriorityManager()
        self.load_dataset()

    def load_dataset(self) -> Dict[str, Any]:
        with open(self.data_path, "r", encoding="utf-8") as f:
            self.raw_data = json.load(f)

        # Update priority configuration from dataset if present
        if "priority_order" in self.raw_data:
            self.priority_manager.update_config(
                self.raw_data["priority_order"],
                self.raw_data.get("role_category_cap")
            )
        return self.raw_data

    def get_all_booking_requests(self) -> List[Dict[str, Any]]:
        return list(self.raw_data.get("booking_requests", []))

    def get_cancellations(self) -> List[Dict[str, Any]]:
        return list(self.raw_data.get("cancellations", []))

    def get_cancelled_ids(self) -> set:
        return {c["request_id"] for c in self.get_cancellations()}

    def sync_to_database(self) -> int:
        """
        Syncs booking requests into the SQLite database.
        Preserves existing decisions and records cancellations accurately.
        """
        requests = self.get_all_booking_requests()
        cancellations = {c["request_id"]: c for c in self.get_cancellations()}

        conn = get_connection()
        cur = conn.cursor()

        synced_count = 0
        for req in requests:
            req_id = req["id"]
            eff_cat = self.priority_manager.get_effective_category(req)

            # Check if cancellation exists
            c_info = cancellations.get(req_id)
            is_cancelled = 1 if c_info else 0
            cancelled_at = c_info.get("cancelled_at") if c_info else None
            cancelled_by = c_info.get("by") if c_info else None
            cancellation_note = c_info.get("note") if c_info else None

            # Check if record already exists
            cur.execute("SELECT id, status, is_cancelled FROM booking_requests WHERE id = ?", (req_id,))
            row = cur.fetchone()

            if row:
                # Update metadata while preserving decision status unless cancelled
                new_status = "cancelled" if is_cancelled else row["status"]
                cur.execute("""
                    UPDATE booking_requests
                    SET title = ?,
                        requester = ?,
                        role = ?,
                        department = ?,
                        requested_category = ?,
                        effective_category = ?,
                        attendance = ?,
                        duration_periods = ?,
                        room_types_json = ?,
                        windows_json = ?,
                        needs_json = ?,
                        mandatory_for_groups_json = ?,
                        requested_room = ?,
                        series_id = ?,
                        raw_text = ?,
                        is_cancelled = ?,
                        cancelled_at = ?,
                        cancelled_by = ?,
                        cancellation_note = ?,
                        status = CASE WHEN ? = 1 THEN 'cancelled' ELSE status END
                    WHERE id = ?
                """, (
                    req.get("title"),
                    req.get("requester"),
                    req["role"],
                    req.get("department"),
                    req["requested_category"],
                    eff_cat,
                    req["attendance"],
                    req["duration_periods"],
                    json.dumps(req["room_types"]),
                    json.dumps(req["windows"]),
                    json.dumps(req.get("needs", [])),
                    json.dumps(req.get("mandatory_for_groups", [])),
                    req.get("requested_room"),
                    req.get("series_id"),
                    req.get("raw_text"),
                    is_cancelled,
                    cancelled_at,
                    cancelled_by,
                    cancellation_note,
                    is_cancelled,
                    req_id
                ))
            else:
                status = "cancelled" if is_cancelled else "pending"
                decision_reason = f"Cancelled by {cancelled_by}: {cancellation_note}" if is_cancelled else None
                cur.execute("""
                    INSERT INTO booking_requests (
                        id, title, requester, raw_text, role, department,
                        requested_category, effective_category, attendance,
                        duration_periods, room_types_json, windows_json,
                        needs_json, mandatory_for_groups_json, requested_room,
                        series_id, status, submitted_at, created_by,
                        is_cancelled, cancelled_at, cancelled_by, cancellation_note,
                        decision_reason
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    req_id,
                    req.get("title"),
                    req.get("requester"),
                    req.get("raw_text"),
                    req["role"],
                    req.get("department"),
                    req["requested_category"],
                    eff_cat,
                    req["attendance"],
                    req["duration_periods"],
                    json.dumps(req["room_types"]),
                    json.dumps(req["windows"]),
                    json.dumps(req.get("needs", [])),
                    json.dumps(req.get("mandatory_for_groups", [])),
                    req.get("requested_room"),
                    req.get("series_id"),
                    status,
                    req["submitted_at"],
                    req.get("requester"),
                    is_cancelled,
                    cancelled_at,
                    cancelled_by,
                    cancellation_note,
                    decision_reason
                ))
            synced_count += 1

        conn.commit()
        conn.close()
        return synced_count
