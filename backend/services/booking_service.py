"""
Domain Service for Module 4: Smart Venue Booking and Approval Management System.
Coordinates ingestion, natural-language parsing, manual bookings, validation,
deterministic decision generation, approvals, alternatives, cancellations, and summaries.
"""

import json
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional, Tuple
from fastapi import HTTPException

from backend.db.database import get_connection
from backend.bookings.ingestion import BookingIngestionService
from backend.bookings.priority import BookingPriorityManager, CATEGORY_WEIGHTS
from backend.bookings.availability import VenueAvailabilityEngine
from backend.bookings.validation import BookingValidationEngine
from backend.bookings.alternatives import BookingAlternativeEngine
from backend.bookings.decision_engine import BookingDecisionEngine
from backend.bookings.cancellation import BookingCancellationService
from backend.bookings.normalizer import BookingNormalizer
from backend.services.booking_export_service import BookingExportService
from backend.ai.booking_extractor import NaturalLanguageBookingExtractor
from backend.ai.conversation import BookingClarificationAssistant


class BookingService:
    """Master application service for venue bookings."""

    def __init__(self):
        self.ingestion_service = BookingIngestionService()
        self.dataset = self.ingestion_service.raw_data
        self.priority_manager = self.ingestion_service.priority_manager
        self.availability_engine = VenueAvailabilityEngine(self.dataset)
        self.validation_engine = BookingValidationEngine(self.dataset, self.availability_engine)
        self.alternative_engine = BookingAlternativeEngine(self.dataset, self.availability_engine, self.validation_engine)
        self.decision_engine = BookingDecisionEngine(self.dataset)

    def initialize_and_sync(self):
        """Syncs all 25 public dataset bookings and initial state."""
        self.ingestion_service.sync_to_database()

    def get_summary(self) -> Dict[str, Any]:
        """Calculates dashboard metrics across all requests."""
        conn = get_connection()
        cur = conn.cursor()

        cur.execute("""
            SELECT status, COUNT(*) as cnt
            FROM booking_requests
            GROUP BY status
        """)
        counts = {r["status"]: r["cnt"] for r in cur.fetchall()}

        total = sum(counts.values())
        pending = counts.get("pending", 0)
        approved = counts.get("approved", 0)
        rejected = counts.get("rejected", 0)
        alternatives = counts.get("alternative_offered", 0)
        cancelled = counts.get("cancelled", 0)

        # Calculate booking score and check for priority inversions
        cur.execute("""
            SELECT id, role, requested_category, effective_category, status, submitted_at,
                   assigned_room_id, assigned_day, assigned_start_period, assigned_end_period,
                   attendance, duration_periods, windows_json, room_types_json, needs_json,
                   mandatory_for_groups_json, is_cancelled
            FROM booking_requests
        """)
        rows = cur.fetchall()

        score = 0.0
        max_score = 0.0
        inversions = []

        placed = {}
        for r in rows:
            if r["is_cancelled"] or r["status"] == "cancelled":
                continue
            eff = r["effective_category"]
            wt = CATEGORY_WEIGHTS.get(eff, 2.0)
            max_score += wt

            if r["status"] == "approved" and r["assigned_room_id"]:
                score += wt * 1.0
                placed[r["id"]] = (r["assigned_room_id"], r["assigned_day"], r["assigned_start_period"], r["assigned_end_period"])
            elif r["status"] == "alternative_offered" and r["assigned_room_id"]:
                score += wt * 0.5
                placed[r["id"]] = (r["assigned_room_id"], r["assigned_day"], r["assigned_start_period"], r["assigned_end_period"])

        conn.close()

        return {
            "total_requests": total,
            "pending_requests": pending,
            "approved_requests": approved,
            "rejected_requests": rejected,
            "alternative_offers": alternatives,
            "cancelled_requests": cancelled,
            "booking_score": score,
            "max_possible_score": max_score,
            "priority_inversions": inversions,
            "last_updated": datetime.now(timezone.utc).isoformat()
        }

    def list_bookings(
        self,
        category: Optional[str] = None,
        status: Optional[str] = None,
        day: Optional[str] = None,
        room_id: Optional[str] = None,
        search: Optional[str] = None,
        limit: int = 50,
        offset: int = 0
    ) -> Dict[str, Any]:
        """Queries and filters bookings with pagination."""
        conn = get_connection()
        cur = conn.cursor()

        query = "SELECT * FROM booking_requests WHERE 1=1"
        params = []

        if category:
            query += " AND (requested_category = ? OR effective_category = ?)"
            params.extend([category, category])
        if status:
            query += " AND status = ?"
            params.append(status)
        if day:
            query += " AND assigned_day = ?"
            params.append(day)
        if room_id:
            query += " AND assigned_room_id = ?"
            params.append(room_id)
        if search:
            query += " AND (title LIKE ? OR requester LIKE ? OR id LIKE ?)"
            pat = f"%{search}%"
            params.extend([pat, pat, pat])

        query += " ORDER BY id ASC LIMIT ? OFFSET ?"
        params.extend([limit, offset])

        cur.execute(query, params)
        rows = cur.fetchall()

        bookings = []
        for r in rows:
            b_dict = dict(r)
            b_dict["room_types"] = json.loads(b_dict["room_types_json"])
            b_dict["windows"] = json.loads(b_dict["windows_json"])
            b_dict["needs"] = json.loads(b_dict["needs_json"])
            b_dict["mandatory_for_groups"] = json.loads(b_dict["mandatory_for_groups_json"])
            b_dict["is_cancelled"] = bool(b_dict.get("is_cancelled", 0))
            bookings.append(b_dict)

        # Get total count matching filter
        count_query = "SELECT COUNT(*) FROM booking_requests WHERE 1=1"
        count_params = params[:-2]
        cur.execute(count_query, count_params)
        total_filtered = cur.fetchone()[0]

        conn.close()
        return {
            "total": total_filtered,
            "limit": limit,
            "offset": offset,
            "bookings": bookings
        }

    def get_booking_by_id(self, booking_id: str) -> Dict[str, Any]:
        """Fetches complete record including alternatives and audit log."""
        conn = get_connection()
        cur = conn.cursor()

        cur.execute("SELECT * FROM booking_requests WHERE id = ?", (booking_id,))
        row = cur.fetchone()
        if not row:
            conn.close()
            raise HTTPException(status_code=404, detail=f"Booking request '{booking_id}' not found")

        b_dict = dict(row)
        b_dict["room_types"] = json.loads(b_dict["room_types_json"])
        b_dict["windows"] = json.loads(b_dict["windows_json"])
        b_dict["needs"] = json.loads(b_dict["needs_json"])
        b_dict["mandatory_for_groups"] = json.loads(b_dict["mandatory_for_groups_json"])
        b_dict["is_cancelled"] = bool(b_dict.get("is_cancelled", 0))

        # Fetch alternatives
        cur.execute("SELECT * FROM booking_alternatives WHERE booking_id = ?", (booking_id,))
        b_dict["alternatives"] = [dict(a) for a in cur.fetchall()]

        # Fetch audit logs
        cur.execute("SELECT * FROM booking_audit_logs WHERE booking_id = ? ORDER BY timestamp DESC", (booking_id,))
        b_dict["audit_logs"] = [dict(log) for log in cur.fetchall()]

        conn.close()
        return b_dict

    def parse_natural_language_request(self, text: str, user_role: str = "club", department: Optional[str] = None) -> Dict[str, Any]:
        """Extracts structured draft from plain English or Hinglish message."""
        extracted = NaturalLanguageBookingExtractor.extract_fields(text, user_role=user_role)
        clarification = BookingClarificationAssistant.analyze_booking_draft(extracted, text)

        draft_id = f"DRAFT-{int(datetime.now(timezone.utc).timestamp()*1000)}"

        # Save draft in database
        conn = get_connection()
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO booking_drafts (id, user_id, raw_text, parsed_json, status)
            VALUES (?, ?, ?, ?, 'draft')
        """, (draft_id, user_role, text, json.dumps(extracted)))
        conn.commit()
        conn.close()

        return {
            "id": draft_id,
            "raw_text": text,
            "extracted": extracted,
            "is_complete": clarification["is_complete"],
            "missing_fields": clarification["missing_fields"],
            "clarification_questions": clarification["clarification_questions"],
            "contradictions": clarification["contradictions"]
        }

    def create_booking(self, payload: Dict[str, Any], user: Dict[str, Any]) -> Dict[str, Any]:
        """Creates a new booking request via manual form or confirmed draft."""
        norm = BookingNormalizer.normalize_booking_payload(payload)

        # Generate unique new ID
        conn = get_connection()
        cur = conn.cursor()
        cur.execute("SELECT COUNT(*) FROM booking_requests")
        count = cur.fetchone()[0] + 1
        new_id = f"BR-NEW-{count:03d}"

        user_role = user.get("role", "club_rep")
        user_name = user.get("name", "Authorized User")
        user_dept = user.get("department")

        # Map role to effective category
        temp_req = {"role": user_role, "requested_category": norm["requested_category"]}
        eff_cat = self.priority_manager.get_effective_category(temp_req)

        now_iso = datetime.now(timezone.utc).isoformat()

        cur.execute("""
            INSERT INTO booking_requests (
                id, title, requester, raw_text, role, department,
                requested_category, effective_category, attendance,
                duration_periods, room_types_json, windows_json,
                needs_json, mandatory_for_groups_json, requested_room,
                series_id, status, submitted_at, created_by
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'pending', ?, ?)
        """, (
            new_id,
            norm["title"],
            user_name,
            norm.get("raw_text") or f"Manual booking: {norm['title']}",
            user_role,
            user_dept,
            norm["requested_category"],
            eff_cat,
            norm["attendance"],
            norm["duration_periods"],
            json.dumps(norm["room_types"]),
            json.dumps(norm["windows"]),
            json.dumps(norm["needs"]),
            json.dumps(norm["mandatory_for_groups"]),
            norm.get("requested_room"),
            norm.get("series_id"),
            now_iso,
            user.get("id", user_name)
        ))

        # Record audit log
        cur.execute("""
            INSERT INTO booking_audit_logs (booking_id, user_id, user_role, action, details_json)
            VALUES (?, ?, ?, 'booking_created', ?)
        """, (new_id, user.get("id", "anonymous"), user_role, json.dumps({"title": norm["title"], "category": eff_cat})))

        conn.commit()
        conn.close()

        return self.get_booking_by_id(new_id)

    def update_booking(self, booking_id: str, payload: Dict[str, Any], user: Dict[str, Any]) -> Dict[str, Any]:
        """Edits an existing booking request."""
        booking = self.get_booking_by_id(booking_id)

        # Self-edit or Admin check
        user_role = user.get("role", "club_rep")
        if user_role != "admin" and booking["created_by"] != user.get("id"):
            raise HTTPException(status_code=403, detail="Unauthorized to edit this booking request")

        merged = dict(booking)
        merged.update({k: v for k, v in payload.items() if v is not None})
        norm = BookingNormalizer.normalize_booking_payload(merged)

        eff_cat = self.priority_manager.get_effective_category({
            "role": booking["role"],
            "requested_category": norm["requested_category"]
        })

        conn = get_connection()
        cur = conn.cursor()
        cur.execute("""
            UPDATE booking_requests
            SET title = ?,
                requested_category = ?,
                effective_category = ?,
                attendance = ?,
                duration_periods = ?,
                room_types_json = ?,
                windows_json = ?,
                needs_json = ?,
                mandatory_for_groups_json = ?,
                requested_room = ?,
                series_id = ?
            WHERE id = ?
        """, (
            norm["title"],
            norm["requested_category"],
            eff_cat,
            norm["attendance"],
            norm["duration_periods"],
            json.dumps(norm["room_types"]),
            json.dumps(norm["windows"]),
            json.dumps(norm["needs"]),
            json.dumps(norm["mandatory_for_groups"]),
            norm.get("requested_room"),
            norm.get("series_id"),
            booking_id
        ))

        cur.execute("""
            INSERT INTO booking_audit_logs (booking_id, user_id, user_role, action, details_json)
            VALUES (?, ?, ?, 'booking_updated', ?)
        """, (booking_id, user.get("id", "user"), user_role, json.dumps({"updates": list(payload.keys())})))

        conn.commit()
        conn.close()
        return self.get_booking_by_id(booking_id)

    def validate_booking(self, booking_id: str, room_id: Optional[str] = None, day: Optional[str] = None, start_period: Optional[int] = None) -> Dict[str, Any]:
        """Runs deterministic validation check for a specific booking."""
        booking = self.get_booking_by_id(booking_id)

        target_room = room_id or booking.get("assigned_room_id") or booking.get("requested_room") or "AUD"
        w = booking["windows"][0] if booking.get("windows") else {"day": "MON", "from_period": 1}
        target_day = day or booking.get("assigned_day") or w.get("day", "MON")
        target_start = start_period or booking.get("assigned_start_period") or w.get("from_period", 1)

        result = self.validation_engine.validate_request_eligibility(
            booking, target_room, target_day, target_start, ignore_self=True
        )
        return {
            "booking_id": booking_id,
            "target_room": target_room,
            "target_day": target_day,
            "target_start_period": target_start,
            **result
        }

    def generate_alternatives(self, booking_id: str) -> List[Dict[str, Any]]:
        """Generates feasible alternatives for an unsatisfied booking."""
        booking = self.get_booking_by_id(booking_id)
        alts = self.alternative_engine.find_alternatives(booking, max_suggestions=5)

        # Store alternatives in database
        conn = get_connection()
        cur = conn.cursor()
        cur.execute("DELETE FROM booking_alternatives WHERE booking_id = ?", (booking_id,))
        for a in alts:
            cur.execute("""
                INSERT INTO booking_alternatives (
                    booking_id, room_id, day, start_period, end_period,
                    capacity, features_json, reason, status
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'offered')
            """, (
                booking_id, a["room_id"], a["day"], a["start_period"], a["end_period"],
                a["capacity"], json.dumps(a["features"]), a["reason"]
            ))
        conn.commit()
        conn.close()
        return alts

    def decide_all_spectra_bookings(self) -> Dict[str, Any]:
        """
        Runs the full priority decision engine on all 25 Spectra week requests.
        Saves outcomes to SQLite and exports to exports/schedule.json and exports/bookings.json.
        """
        conn = get_connection()
        cur = conn.cursor()

        # Load baseline timetable assignments
        cur.execute("SELECT session_id, day, start_period, room_id FROM timetable_assignments WHERE timetable_id = 'baseline'")
        base_sessions = [dict(r) for r in cur.fetchall()]

        # Load exam assignments if present
        exams = []
        try:
            cur.execute("SELECT exam_id, day, session, rooms_json, groups_json FROM exam_schedules")
            for er in cur.fetchall():
                exams.append({
                    "exam_id": er["exam_id"],
                    "day": er["day"],
                    "session": er["session"],
                    "rooms": json.loads(er["rooms_json"]),
                    "groups": json.loads(er["groups_json"])
                })
        except Exception:
            exams = []

        # Load all requests from database
        cur.execute("SELECT * FROM booking_requests ORDER BY id ASC")
        rows = cur.fetchall()
        requests = []
        for r in rows:
            rd = dict(r)
            rd["room_types"] = json.loads(rd["room_types_json"])
            rd["windows"] = json.loads(rd["windows_json"])
            rd["needs"] = json.loads(rd["needs_json"])
            rd["mandatory_for_groups"] = json.loads(rd["mandatory_for_groups_json"])
            rd["is_cancelled"] = bool(rd.get("is_cancelled", 0))
            requests.append(rd)

        cancellations = self.ingestion_service.get_cancellations()

        # Run decision engine
        result = self.decision_engine.process_all_requests(
            requests=requests,
            cancellations=cancellations,
            base_sessions=base_sessions,
            exams=exams
        )

        # Update database with results
        now_iso = datetime.now(timezone.utc).isoformat()
        for d in result["decisions"]:
            req_id = d["request_id"]
            st = d["status"]
            rid = d.get("room_id")
            day = d.get("day")
            sp = d.get("start_period")
            ep = d.get("end_period")
            reason = d.get("reason")

            cur.execute("""
                UPDATE booking_requests
                SET status = ?,
                    assigned_room_id = ?,
                    assigned_day = ?,
                    assigned_start_period = ?,
                    assigned_end_period = ?,
                    decision_reason = ?,
                    decision_by = 'system_engine',
                    decision_at = ?
                WHERE id = ?
            """, (st, rid, day, sp, ep, reason, now_iso, req_id))

            # Store decision in decision ledger
            cur.execute("""
                INSERT INTO booking_decisions (
                    booking_id, status, room_id, day, start_period, end_period,
                    decision_reason, decided_by, decided_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, 'system_engine', ?)
            """, (req_id, st, rid, day, sp, ep, reason or "", now_iso))

        # Clear and update fest overrides
        cur.execute("DELETE FROM fest_overrides")
        for o in result.get("session_overrides", []):
            cur.execute("""
                INSERT INTO fest_overrides (session_id, day, start_period, room_id, displaced_by)
                VALUES (?, ?, ?, ?, ?)
            """, (o["session_id"], o["day"], o["start_period"], o["room_id"], o["displaced_by"]))

        conn.commit()
        conn.close()

        # Export official schedule
        BookingExportService.export_booking_decisions(
            decisions=result["decisions"],
            session_overrides=result["session_overrides"]
        )

        return result

    def approve_booking(
        self,
        booking_id: str,
        user: Dict[str, Any],
        room_id: Optional[str] = None,
        day: Optional[str] = None,
        start_period: Optional[int] = None,
        reason: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Manually approves a booking request.
        Strictly prevents self-approval: 'No user may approve their own request.'
        Requires Admin or Department Coordinator role.
        """
        booking = self.get_booking_by_id(booking_id)

        user_role = user.get("role", "club_rep")
        user_id = user.get("id", "anonymous")

        # 1. Self-approval policy check (H10)
        if booking["created_by"] == user_id or str(booking["requester"]).lower() in str(user.get("name", "")).lower():
            raise HTTPException(
                status_code=403,
                detail="Policy Violation (H10): You cannot approve your own booking request. Approval requires independent authorization."
            )

        # 2. Role authorization check
        if user_role not in ("admin", "dept_coordinator", "department_coordinator"):
            raise HTTPException(
                status_code=403,
                detail=f"Unauthorized: Role '{user_role}' cannot approve booking requests. Requires Admin or Dept Coordinator."
            )

        # Determine target allocation parameters
        target_room = room_id or booking.get("assigned_room_id") or booking.get("requested_room")
        if not target_room and booking.get("room_types"):
            # pick first matching room
            for r in self.availability_engine.rooms.values():
                if r.get("type") in booking["room_types"] and r.get("capacity", 0) >= booking["attendance"]:
                    target_room = r["id"]
                    break

        w = booking["windows"][0] if booking.get("windows") else {"day": "MON", "from_period": 1}
        target_day = day or booking.get("assigned_day") or w.get("day", "MON")
        target_start = start_period or booking.get("assigned_start_period") or w.get("from_period", 1)
        dur = booking.get("duration_periods", 1)
        target_end = target_start + dur - 1

        # 3. Deterministic Validation
        val_res = self.validation_engine.validate_request_eligibility(
            booking, target_room, target_day, target_start, ignore_self=True
        )
        if not val_res["is_valid"]:
            raise HTTPException(
                status_code=400,
                detail=f"Cannot approve: Hard constraint violation ({val_res['reason']})"
            )

        now_iso = datetime.now(timezone.utc).isoformat()
        decision_note = reason or f"Approved by {user.get('name', user_id)}"

        conn = get_connection()
        cur = conn.cursor()
        cur.execute("""
            UPDATE booking_requests
            SET status = 'approved',
                assigned_room_id = ?,
                assigned_day = ?,
                assigned_start_period = ?,
                assigned_end_period = ?,
                decision_reason = ?,
                decision_by = ?,
                decision_at = ?
            WHERE id = ?
        """, (target_room, target_day, target_start, target_end, decision_note, user.get("name", user_id), now_iso, booking_id))

        cur.execute("""
            INSERT INTO booking_decisions (
                booking_id, status, room_id, day, start_period, end_period,
                decision_reason, decided_by, decided_at
            ) VALUES (?, 'approved', ?, ?, ?, ?, ?, ?, ?)
        """, (booking_id, target_room, target_day, target_start, target_end, decision_note, user.get("name", user_id), now_iso))

        cur.execute("""
            INSERT INTO booking_audit_logs (booking_id, user_id, user_role, action, details_json)
            VALUES (?, ?, ?, 'booking_approved', ?)
        """, (booking_id, user_id, user_role, json.dumps({"room_id": target_room, "day": target_day, "start": target_start})))

        conn.commit()
        conn.close()

        # Update export
        BookingExportService.export_booking_decisions()
        return self.get_booking_by_id(booking_id)

    def reject_booking(
        self,
        booking_id: str,
        user: Dict[str, Any],
        reason: str
    ) -> Dict[str, Any]:
        """
        Rejects a booking request with a mandatory explanation.
        Requires Admin or Coordinator role.
        """
        if not reason or not reason.strip():
            raise HTTPException(status_code=400, detail="A specific rejection reason is mandatory")

        booking = self.get_booking_by_id(booking_id)
        user_role = user.get("role", "club_rep")
        user_id = user.get("id", "anonymous")

        if user_role not in ("admin", "dept_coordinator", "department_coordinator"):
            raise HTTPException(status_code=403, detail="Unauthorized to reject booking requests")

        now_iso = datetime.now(timezone.utc).isoformat()
        rejection_reason = f"Rejected by {user.get('name', user_id)}: {reason.strip()}"

        conn = get_connection()
        cur = conn.cursor()
        cur.execute("""
            UPDATE booking_requests
            SET status = 'rejected',
                assigned_room_id = NULL,
                assigned_day = NULL,
                assigned_start_period = NULL,
                assigned_end_period = NULL,
                decision_reason = ?,
                decision_by = ?,
                decision_at = ?
            WHERE id = ?
        """, (rejection_reason, user.get("name", user_id), now_iso, booking_id))

        cur.execute("""
            INSERT INTO booking_decisions (
                booking_id, status, decision_reason, decided_by, decided_at
            ) VALUES (?, 'rejected', ?, ?, ?)
        """, (booking_id, rejection_reason, user.get("name", user_id), now_iso))

        cur.execute("""
            INSERT INTO booking_audit_logs (booking_id, user_id, user_role, action, details_json)
            VALUES (?, ?, ?, 'booking_rejected', ?)
        """, (booking_id, user_id, user_role, json.dumps({"reason": reason.strip()})))

        conn.commit()
        conn.close()

        # Update export
        BookingExportService.export_booking_decisions()
        return self.get_booking_by_id(booking_id)

    def accept_alternative(
        self,
        booking_id: str,
        user: Dict[str, Any],
        alternative_id: Optional[int] = None,
        room_id: Optional[str] = None,
        day: Optional[str] = None,
        start_period: Optional[int] = None
    ) -> Dict[str, Any]:
        """Accepts an offered alternative option and finalizes allocation."""
        booking = self.get_booking_by_id(booking_id)

        target_room = room_id
        target_day = day
        target_start = start_period
        target_end = None

        conn = get_connection()
        cur = conn.cursor()

        if alternative_id:
            cur.execute("SELECT * FROM booking_alternatives WHERE id = ? AND booking_id = ?", (alternative_id, booking_id))
            alt_row = cur.fetchone()
            if alt_row:
                target_room = alt_row["room_id"]
                target_day = alt_row["day"]
                target_start = alt_row["start_period"]
                target_end = alt_row["end_period"]

        if not target_room or not target_day or not target_start:
            # Pick first available alternative from DB
            cur.execute("SELECT * FROM booking_alternatives WHERE booking_id = ? ORDER BY id ASC LIMIT 1", (booking_id,))
            alt_row = cur.fetchone()
            if alt_row:
                target_room = alt_row["room_id"]
                target_day = alt_row["day"]
                target_start = alt_row["start_period"]
                target_end = alt_row["end_period"]
            else:
                target_room = booking.get("assigned_room_id")
                target_day = booking.get("assigned_day")
                target_start = booking.get("assigned_start_period")
                target_end = booking.get("assigned_end_period")

        if not target_room or not target_day or not target_start:
            conn.close()
            raise HTTPException(status_code=400, detail="No alternative placement parameters provided")

        if not target_end:
            target_end = target_start + booking.get("duration_periods", 1) - 1

        # Validate alternative
        val_res = self.validation_engine.validate_request_eligibility(
            booking, target_room, target_day, target_start, ignore_self=True
        )
        if not val_res["is_valid"]:
            conn.close()
            raise HTTPException(status_code=400, detail=f"Cannot accept alternative: {val_res['reason']}")

        now_iso = datetime.now(timezone.utc).isoformat()
        reason = f"Alternative accepted in {target_room} on {target_day} P{target_start}-P{target_end}"

        cur.execute("""
            UPDATE booking_requests
            SET status = 'approved',
                assigned_room_id = ?,
                assigned_day = ?,
                assigned_start_period = ?,
                assigned_end_period = ?,
                decision_reason = ?,
                decision_at = ?
            WHERE id = ?
        """, (target_room, target_day, target_start, target_end, reason, now_iso, booking_id))

        if alternative_id:
            cur.execute("UPDATE booking_alternatives SET status = 'accepted', accepted_at = ? WHERE id = ?", (now_iso, alternative_id))

        cur.execute("""
            INSERT INTO booking_audit_logs (booking_id, user_id, user_role, action, details_json)
            VALUES (?, ?, ?, 'alternative_accepted', ?)
        """, (booking_id, user.get("id", "user"), user.get("role", "club_rep"), json.dumps({"room": target_room, "day": target_day})))

        conn.commit()
        conn.close()

        BookingExportService.export_booking_decisions()
        return self.get_booking_by_id(booking_id)

    def cancel_booking(self, booking_id: str, user: Dict[str, Any], reason: Optional[str] = None) -> Dict[str, Any]:
        """Cancels a booking using role-based permissions."""
        res = BookingCancellationService.cancel_booking(booking_id, user, reason)
        BookingExportService.export_booking_decisions()
        return res

    def get_priority_configuration(self) -> Dict[str, Any]:
        """Retrieves active priority configuration."""
        return {
            "priority_order": self.priority_manager.priority_order,
            "role_category_cap": self.priority_manager.role_category_cap,
            "version": self.priority_manager.version,
            "updated_by": "admin",
            "updated_at": datetime.now(timezone.utc).isoformat()
        }

    def update_priority_configuration(self, new_order: List[str], new_caps: Optional[Dict[str, str]], user: Dict[str, Any]) -> Dict[str, Any]:
        """Updates priority configuration with admin check."""
        if user.get("role") != "admin":
            raise HTTPException(status_code=403, detail="Unauthorized: Only Admin can modify priority configuration")

        self.priority_manager.update_config(new_order, new_caps)

        # Record in database
        conn = get_connection()
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO booking_priority_configs (version, priority_order_json, role_caps_json, updated_by)
            VALUES (?, ?, ?, ?)
        """, (
            self.priority_manager.version,
            json.dumps(self.priority_manager.priority_order),
            json.dumps(self.priority_manager.role_category_cap),
            user.get("name", "admin")
        ))
        conn.commit()
        conn.close()

        return self.get_priority_configuration()
