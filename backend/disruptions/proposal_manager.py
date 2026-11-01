"""
Rescheduling Proposal Manager.
Coordinates generation, persistence, side-by-side comparison, and approval/rejection workflows.
Enforces role-based permissions and atomic schedule transitions.
"""

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Any, List, Optional
from fastapi import HTTPException

from backend.db.database import get_connection
from backend.config import EXPORTS_DIR
from backend.disruptions.version_manager import TimetableVersionManager
from backend.services.export_service import export_schedules


class ProposalManager:
    """Manages proposed rescheduling solutions, diffs, and approval workflows."""

    @staticmethod
    def save_proposal(
        proposal_id: str,
        disruption_id: str,
        baseline_id: str,
        target_version_id: str,
        solver_result: Dict[str, Any],
        user_id: str = "admin"
    ) -> Dict[str, Any]:
        """Saves proposal and session assignments to database without overwriting active schedule."""
        conn = get_connection()
        cur = conn.cursor()

        now_iso = datetime.now(timezone.utc).isoformat()

        cur.execute("""
            INSERT OR REPLACE INTO rescheduling_proposals (
                id, disruption_id, baseline_timetable_id, target_timetable_version,
                status, solver_status, solve_time_seconds, sessions_moved,
                time_changed, room_only_changed, unchanged_sessions,
                hard_violations_count, hard_violations_json, soft_penalty,
                diff_json, created_by, created_at
            ) VALUES (?, ?, ?, ?, 'proposed', ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            proposal_id,
            disruption_id,
            baseline_id,
            target_version_id,
            solver_result.get("solver_status", "FEASIBLE"),
            solver_result.get("solve_time_seconds", 0.0),
            solver_result.get("sessions_moved", 0),
            solver_result.get("time_changed", 0),
            solver_result.get("room_only_changed", 0),
            solver_result.get("unchanged_sessions", 0),
            solver_result.get("hard_violations_count", 0),
            json.dumps(solver_result.get("hard_violations", [])),
            solver_result.get("soft_penalty", 0),
            json.dumps(solver_result.get("assignment_items", [])),
            user_id,
            now_iso
        ))

        # Save individual proposal assignments
        cur.execute("DELETE FROM rescheduling_proposal_assignments WHERE proposal_id = ?", (proposal_id,))
        assign_rows = [
            (
                proposal_id,
                item["session_id"],
                item.get("course_id"),
                item.get("faculty_id"),
                json.dumps(item.get("groups", [])),
                item.get("original_day"),
                item.get("original_start_period"),
                item.get("original_room_id"),
                item["proposed_day"],
                item["proposed_start_period"],
                item["proposed_room_id"],
                1 if item.get("is_moved") else 0,
                item.get("change_type", "unchanged"),
                item.get("change_reason")
            )
            for item in solver_result.get("assignment_items", [])
        ]

        cur.executemany("""
            INSERT INTO rescheduling_proposal_assignments (
                proposal_id, session_id, course_id, faculty_id, groups_json,
                original_day, original_start_period, original_room_id,
                proposed_day, proposed_start_period, proposed_room_id,
                is_moved, change_type, change_reason
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, assign_rows)

        # Update disruption status to proposal_generated
        cur.execute("""
            UPDATE disruptions
            SET status = 'proposal_generated'
            WHERE id = ?
        """, (disruption_id,))

        # Record audit log
        cur.execute("""
            INSERT INTO rescheduling_audit_logs (proposal_id, disruption_id, user_id, user_role, action, details_json)
            VALUES (?, ?, ?, 'admin', 'proposal_generated', ?)
        """, (proposal_id, disruption_id, user_id, json.dumps({"moved": solver_result.get("sessions_moved", 0)})))

        conn.commit()
        conn.close()
        return ProposalManager.get_proposal_by_id(proposal_id)

    @staticmethod
    def get_proposal_by_id(proposal_id: str) -> Dict[str, Any]:
        """Retrieves proposal metadata."""
        conn = get_connection()
        cur = conn.cursor()
        cur.execute("SELECT * FROM rescheduling_proposals WHERE id = ?", (proposal_id,))
        row = cur.fetchone()
        conn.close()
        if not row:
            raise HTTPException(status_code=404, detail=f"Rescheduling proposal '{proposal_id}' not found")

        p_dict = dict(row)
        p_dict["hard_violations"] = json.loads(p_dict["hard_violations_json"] or "[]")
        p_dict["diff"] = json.loads(p_dict["diff_json"] or "[]")
        return p_dict

    @staticmethod
    def list_proposals(disruption_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """Lists all rescheduling proposals."""
        conn = get_connection()
        cur = conn.cursor()
        if disruption_id:
            cur.execute("SELECT * FROM rescheduling_proposals WHERE disruption_id = ? ORDER BY created_at DESC", (disruption_id,))
        else:
            cur.execute("SELECT * FROM rescheduling_proposals ORDER BY created_at DESC")
        rows = cur.fetchall()
        conn.close()

        proposals = []
        for r in rows:
            p_dict = dict(r)
            p_dict["hard_violations"] = json.loads(p_dict["hard_violations_json"] or "[]")
            proposals.append(p_dict)
        return proposals

    @staticmethod
    def get_comparison(proposal_id: str) -> Dict[str, Any]:
        """
        Retrieves side-by-side comparison between original baseline and proposed schedule.
        Highlights changed sessions with detailed reasons.
        """
        prop = ProposalManager.get_proposal_by_id(proposal_id)

        conn = get_connection()
        cur = conn.cursor()
        cur.execute("""
            SELECT * FROM rescheduling_proposal_assignments
            WHERE proposal_id = ?
            ORDER BY is_moved DESC, session_id ASC
        """, (proposal_id,))
        rows = cur.fetchall()
        conn.close()

        changed_sessions = []
        all_assignments = []
        for r in rows:
            item = dict(r)
            item["groups"] = json.loads(item["groups_json"] or "[]")
            item["is_moved"] = bool(item["is_moved"])
            all_assignments.append(item)
            if item["is_moved"]:
                changed_sessions.append(item)

        return {
            "proposal_id": proposal_id,
            "disruption_id": prop["disruption_id"],
            "baseline_version": prop["baseline_timetable_id"],
            "proposed_version": prop["target_timetable_version"],
            "summary": {
                "total_sessions": len(all_assignments),
                "sessions_moved": prop["sessions_moved"],
                "time_changed": prop["time_changed"],
                "room_only_changed": prop["room_only_changed"],
                "unchanged_sessions": prop["unchanged_sessions"]
            },
            "validation": {
                "is_valid": prop["hard_violations_count"] == 0,
                "hard_violations_count": prop["hard_violations_count"],
                "hard_violations": prop["hard_violations"],
                "soft_penalty": prop["soft_penalty"]
            },
            "changed_sessions": changed_sessions,
            "all_assignments": all_assignments
        }

    @staticmethod
    def approve_proposal(
        proposal_id: str,
        user: Dict[str, Any],
        reason: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Approves a rescheduling proposal:
        1. Role check: Requires Admin or Dept Coordinator.
        2. Activates the target timetable version atomically.
        3. Updates proposal and disruption statuses to 'approved'.
        4. Exports schedule.json and schedule_after.json.
        """
        user_role = user.get("role", "club_rep")
        user_id = user.get("id", "anonymous")
        if user_role not in ("admin", "dept_coordinator", "department_coordinator"):
            raise HTTPException(
                status_code=403,
                detail=f"Unauthorized: Role '{user_role}' cannot approve timetable rescheduling. Requires Admin."
            )

        prop = ProposalManager.get_proposal_by_id(proposal_id)
        if prop["status"] == "approved":
            return {"status": "already_approved", "proposal_id": proposal_id}

        # Self-approval check: Non-admin users cannot approve proposals they submitted
        if user_role != "admin" and prop.get("created_by") and prop["created_by"] not in ("system", "system_solver") and prop["created_by"] == user_id:
            raise HTTPException(
                status_code=403,
                detail="Policy Violation: Self-approval forbidden. You cannot approve a rescheduling proposal you submitted."
            )

        conn = get_connection()
        cur = conn.cursor()

        # Read proposed session assignments
        cur.execute("""
            SELECT session_id, proposed_day as day, proposed_start_period as start_period, proposed_room_id as room_id
            FROM rescheduling_proposal_assignments
            WHERE proposal_id = ?
        """, (proposal_id,))
        proposed_assignments = [dict(r) for r in cur.fetchall()]

        now_iso = datetime.now(timezone.utc).isoformat()
        decision_note = reason or f"Approved by {user.get('name', user_id)}"

        # 1. Update proposal status
        cur.execute("""
            UPDATE rescheduling_proposals
            SET status = 'approved',
                decided_by = ?,
                decided_at = ?,
                decision_reason = ?
            WHERE id = ?
        """, (user.get("name", user_id), now_iso, decision_note, proposal_id))

        # 2. Update disruption status
        cur.execute("""
            UPDATE disruptions
            SET status = 'approved',
                applied_at = ?,
                applied_by = ?,
                sessions_moved = ?
            WHERE id = ?
        """, (now_iso, user.get("name", user_id), prop["sessions_moved"], prop["disruption_id"]))

        # 3. Record audit log
        cur.execute("""
            INSERT INTO rescheduling_audit_logs (proposal_id, disruption_id, user_id, user_role, action, details_json)
            VALUES (?, ?, ?, ?, 'proposal_approved', ?)
        """, (proposal_id, prop["disruption_id"], user_id, user_role, json.dumps({"sessions_moved": prop["sessions_moved"]})))

        conn.commit()
        conn.close()

        # 4. Activate new timetable version atomically
        TimetableVersionManager.activate_new_version(
            version_id=prop["target_timetable_version"],
            name=f"Rescheduled Timetable ({prop['target_timetable_version']})",
            assignments=proposed_assignments,
            source="disruption_reschedule",
            stats={
                "sessions_moved": prop["sessions_moved"],
                "hard_violations": prop["hard_violations_count"],
                "soft_penalty": prop["soft_penalty"]
            }
        )

        # 5. Export schedule_after.json while preserving exams and fest_week
        schedule_path = EXPORTS_DIR / "schedule.json"
        existing_sched = {}
        if schedule_path.exists():
            try:
                with open(schedule_path, "r", encoding="utf-8") as f:
                    existing_sched = json.load(f)
            except Exception:
                existing_sched = {}

        after_sched = {
            "team": "CIT-DevOps",
            "dataset_id": existing_sched.get("dataset_id", "cit-public-v1"),
            "sessions": proposed_assignments,
            "exams": existing_sched.get("exams", []),
            "fest_week": existing_sched.get("fest_week", {})
        }
        after_path = EXPORTS_DIR / "schedule_after.json"
        after_path.parent.mkdir(parents=True, exist_ok=True)
        with open(after_path, "w", encoding="utf-8") as f:
            json.dump(after_sched, f, indent=2)

        return ProposalManager.get_proposal_by_id(proposal_id)

    @staticmethod
    def reject_proposal(
        proposal_id: str,
        user: Dict[str, Any],
        reason: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Rejects a rescheduling proposal:
        Preserves existing approved timetable intact.
        """
        user_role = user.get("role", "club_rep")
        user_id = user.get("id", "anonymous")
        if user_role not in ("admin", "dept_coordinator", "department_coordinator"):
            raise HTTPException(status_code=403, detail="Unauthorized to reject proposals")

        prop = ProposalManager.get_proposal_by_id(proposal_id)
        now_iso = datetime.now(timezone.utc).isoformat()
        decision_note = reason or f"Rejected by {user.get('name', user_id)}"

        conn = get_connection()
        cur = conn.cursor()
        cur.execute("""
            UPDATE rescheduling_proposals
            SET status = 'rejected',
                decided_by = ?,
                decided_at = ?,
                decision_reason = ?
            WHERE id = ?
        """, (user.get("name", user_id), now_iso, decision_note, proposal_id))

        cur.execute("""
            UPDATE disruptions
            SET status = 'rejected'
            WHERE id = ?
        """, (prop["disruption_id"],))

        cur.execute("""
            INSERT INTO rescheduling_audit_logs (proposal_id, disruption_id, user_id, user_role, action, details_json)
            VALUES (?, ?, ?, ?, 'proposal_rejected', ?)
        """, (proposal_id, prop["disruption_id"], user_id, user_role, json.dumps({"reason": decision_note})))

        conn.commit()
        conn.close()
        return ProposalManager.get_proposal_by_id(proposal_id)
