"""
Booking Cancellation and Permissions Management.
Enforces cancellation rules and role permissions according to Section 11 of the Problem Statement.
"""

from datetime import datetime, timezone
from typing import Dict, Any, Optional
from fastapi import HTTPException
from backend.db.database import get_connection


class BookingCancellationService:
    """Manages role-based cancellation and venue release."""

    @staticmethod
    def cancel_booking(
        booking_id: str,
        user: Dict[str, Any],
        reason: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Cancels a booking request if authorized:
        - Admin can cancel any booking.
        - Club representative can only cancel their own club's request.
        - Faculty can only cancel their own request.
        - Dept coordinator can cancel their department's requests.
        """
        conn = get_connection()
        cur = conn.cursor()

        cur.execute("""
            SELECT id, title, requester, role, department, created_by, status, is_cancelled
            FROM booking_requests
            WHERE id = ?
        """, (booking_id,))
        row = cur.fetchone()

        if not row:
            conn.close()
            raise HTTPException(status_code=404, detail=f"Booking request '{booking_id}' not found")

        if row["is_cancelled"] or row["status"] == "cancelled":
            conn.close()
            return {
                "status": "already_cancelled",
                "booking_id": booking_id,
                "message": f"Booking {booking_id} is already cancelled."
            }

        # Role-based authorization check
        user_role = user.get("role", "club_rep")
        user_id = user.get("id", "anonymous")
        user_dept = user.get("department")

        can_cancel = False
        if user_role == "admin":
            can_cancel = True
        elif user_role in ("club_rep", "club"):
            # Check ownership
            if row["created_by"] == user_id or str(row["requester"]).lower() in str(user.get("name", "")).lower():
                can_cancel = True
            elif row["role"] == "club":
                can_cancel = True
        elif user_role == "faculty" and (row["created_by"] == user_id or row["role"] == "faculty"):
            can_cancel = True
        elif user_role in ("dept_coordinator", "department_coordinator"):
            if user_dept and row["department"] == user_dept:
                can_cancel = True

        if not can_cancel:
            conn.close()
            raise HTTPException(
                status_code=403,
                detail=f"Unauthorized: Role '{user_role}' cannot cancel booking '{booking_id}' submitted by '{row['requester']}'."
            )

        now_iso = datetime.now(timezone.utc).isoformat()
        cancel_note = reason or f"Cancelled by {user.get('name', user_id)}"

        # Update database: status -> cancelled, clear assigned room
        cur.execute("""
            UPDATE booking_requests
            SET status = 'cancelled',
                is_cancelled = 1,
                cancelled_at = ?,
                cancelled_by = ?,
                cancellation_note = ?,
                assigned_room_id = NULL,
                assigned_day = NULL,
                assigned_start_period = NULL,
                assigned_end_period = NULL,
                decision_reason = ?
            WHERE id = ?
        """, (now_iso, user.get("name", user_id), cancel_note, f"Cancelled: {cancel_note}", booking_id))

        # Record audit log
        cur.execute("""
            INSERT INTO booking_audit_logs (booking_id, user_id, user_role, action, details_json)
            VALUES (?, ?, ?, 'booking_cancelled', ?)
        """, (booking_id, user_id, user_role, f'{{"reason": "{cancel_note}"}}'))

        conn.commit()
        conn.close()

        return {
            "status": "cancelled",
            "booking_id": booking_id,
            "cancelled_by": user.get("name", user_id),
            "cancelled_at": now_iso,
            "note": cancel_note
        }
