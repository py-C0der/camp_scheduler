"""
Role-based Recipient Resolution Service for CIT Campus Notifications.
Resolves targeted user IDs, roles, and contact details from the database
without spamming unrelated users.
"""

from typing import List, Dict, Any, Set, Tuple
import sqlite3
from backend.db.database import get_connection
from backend.notifications.events import EventTypes, NotificationEvent


class RecipientResolver:
    """
    Deterministically resolves intended recipient user records for any event.
    """

    def __init__(self, db_conn_factory=get_connection):
        self.get_conn = db_conn_factory

    def resolve_recipients(self, event: NotificationEvent) -> List[Dict[str, Any]]:
        """
        Returns list of recipient dicts:
        [{'user_id': ..., 'name': ..., 'email': ..., 'role': ..., 'department': ..., 'faculty_id': ...}]
        """
        conn = self.get_conn()
        cur = conn.cursor()

        payload = event.payload or {}
        recipients_map: Dict[str, Dict[str, Any]] = {}

        def add_user(row):
            if row and row["id"] not in recipients_map:
                recipients_map[row["id"]] = {
                    "user_id": row["id"],
                    "name": row["name"],
                    "email": row["email"],
                    "role": row["role"],
                    "department": row["department"],
                    "faculty_id": row["faculty_id"]
                }

        # 1. ADMINS: always get system alerts, critical disruptions, new timetables, and approval requests
        if event.severity in ("critical", "high") or event.category in ("approval", "disruption") or event.event_type in (
            EventTypes.TIMETABLE_APPROVED, EventTypes.EXAM_SCHEDULE_APPROVED, EventTypes.DISRUPTION_REPORTED, EventTypes.BOOKING_SUBMITTED
        ):
            cur.execute("SELECT * FROM users WHERE role = 'admin'")
            for r in cur.fetchall():
                add_user(r)

        # 2. DEPARTMENT COORDINATORS: get events relevant to their department
        target_depts = set()
        if "department" in payload and payload["department"]:
            target_depts.add(payload["department"].upper())
        if "departments" in payload and isinstance(payload["departments"], list):
            for d in payload["departments"]:
                target_depts.add(str(d).upper())

        if target_depts:
            placeholders = ",".join("?" for _ in target_depts)
            cur.execute(f"SELECT * FROM users WHERE role = 'dept_coordinator' AND UPPER(department) IN ({placeholders})", list(target_depts))
            for r in cur.fetchall():
                add_user(r)
        elif event.category in ("timetable", "examination", "disruption"):
            # If no specific department is targeted, inform all active dept coordinators
            cur.execute("SELECT * FROM users WHERE role = 'dept_coordinator'")
            for r in cur.fetchall():
                add_user(r)

        # 3. FACULTY: get personal timetable/room changes, exam assignments, disruption reschedules
        target_faculty_ids = set()
        if "faculty_id" in payload and payload["faculty_id"]:
            target_faculty_ids.add(str(payload["faculty_id"]))
        if "faculty_ids" in payload and isinstance(payload["faculty_ids"], list):
            for fid in payload["faculty_ids"]:
                target_faculty_ids.add(str(fid))

        if target_faculty_ids:
            placeholders = ",".join("?" for _ in target_faculty_ids)
            cur.execute(f"SELECT * FROM users WHERE role = 'faculty' AND faculty_id IN ({placeholders})", list(target_faculty_ids))
            for r in cur.fetchall():
                add_user(r)
        elif event.event_type in (EventTypes.TIMETABLE_APPROVED, EventTypes.EXAM_SCHEDULE_APPROVED, EventTypes.RESCHEDULING_APPROVED):
            # Broad academic releases notify all faculty
            cur.execute("SELECT * FROM users WHERE role = 'faculty'")
            for r in cur.fetchall():
                add_user(r)

        # 4. CLUB REPRESENTATIVE / REQUESTER: gets own booking updates
        requester_id = payload.get("created_by") or payload.get("requester_id")
        requester_name = payload.get("requester")
        if requester_id:
            cur.execute("SELECT * FROM users WHERE id = ?", (requester_id,))
            r = cur.fetchone()
            if r:
                add_user(r)
        elif requester_name:
            cur.execute("SELECT * FROM users WHERE name LIKE ? OR id LIKE ?", (f"%{requester_name}%", f"%{requester_name}%"))
            for r in cur.fetchall():
                add_user(r)

        # If booking submitted/updated and no specific club rep matched, target club_rep users
        if event.category == "venue_booking" and not any(u["role"] == "club_rep" for u in recipients_map.values()):
            cur.execute("SELECT * FROM users WHERE role = 'club_rep'")
            for r in cur.fetchall():
                add_user(r)

        # Ensure that if still empty, admins receive it as a fallback
        if not recipients_map:
            cur.execute("SELECT * FROM users WHERE role = 'admin'")
            for r in cur.fetchall():
                add_user(r)

        conn.close()
        return list(recipients_map.values())
