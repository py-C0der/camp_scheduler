"""
Application Domain Service for Module 5: Disruption Management and Timetable Rescheduling Engine.
Ties together disruption reporting, impact analysis, CP-SAT rescheduling proposals,
approval workflows, version history, and dashboard metrics.
"""

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Any, List, Optional
from fastapi import HTTPException

from backend.db.database import get_connection
from backend.disruptions.impact_analyzer import DisruptionImpactAnalyzer
from backend.disruptions.reschedule_engine import TimetableReschedulingEngine
from backend.disruptions.proposal_manager import ProposalManager
from backend.disruptions.version_manager import TimetableVersionManager

DATA_PATH = Path(__file__).resolve().parent.parent.parent / "CrunchWeek_StarterPack" / "data" / "cit_public.json"


class DisruptionService:
    """Master service for campus disruption management and rescheduling."""

    def __init__(self):
        with open(DATA_PATH, "r", encoding="utf-8") as f:
            self.dataset = json.load(f)
        self.sessions_dict = {s["id"]: s for s in self.dataset.get("sessions", [])}
        self.rooms_dict = {r["id"]: r for r in self.dataset.get("rooms", [])}
        self.faculty_dict = {f["id"]: f for f in self.dataset.get("faculty", [])}

    def get_dashboard_summary(self) -> Dict[str, Any]:
        """Calculates dashboard metrics across all disruptions and proposals."""
        conn = get_connection()
        cur = conn.cursor()

        cur.execute("SELECT status, COUNT(*) as cnt FROM disruptions GROUP BY status")
        dis_counts = {r["status"]: r["cnt"] for r in cur.fetchall()}

        cur.execute("SELECT status, COUNT(*) as cnt FROM rescheduling_proposals GROUP BY status")
        prop_counts = {r["status"]: r["cnt"] for r in cur.fetchall()}

        cur.execute("SELECT id FROM disruptions ORDER BY rowid DESC LIMIT 1")
        latest = cur.fetchone()
        latest_id = latest["id"] if latest else None

        active_ver = TimetableVersionManager.get_active_timetable_id()

        conn.close()

        total = sum(dis_counts.values())
        open_cnt = dis_counts.get("reported", 0)
        analyzing = dis_counts.get("analyzing", 0) + dis_counts.get("proposal_generated", 0)
        approved_cnt = dis_counts.get("approved", 0)
        rejected_cnt = dis_counts.get("rejected", 0)
        awaiting = prop_counts.get("proposed", 0)

        return {
            "total_disruptions": total,
            "open_disruptions": open_cnt,
            "analyzing_disruptions": analyzing,
            "proposals_awaiting_approval": awaiting,
            "approved_reschedulings": approved_cnt,
            "unresolved_disruptions": open_cnt + analyzing,
            "latest_disruption_id": latest_id,
            "active_timetable_version": active_ver
        }

    def create_disruption(self, payload: Dict[str, Any], user: Dict[str, Any]) -> Dict[str, Any]:
        """Validates and stores a new disruption report."""
        user_role = user.get("role", "club_rep")
        if user_role not in ("admin", "dept_coordinator", "department_coordinator", "faculty"):
            raise HTTPException(status_code=403, detail="Unauthorized: Only Admin, Coordinator, or Faculty can report disruptions.")

        changes = payload.get("changes", [])
        if not changes:
            raise HTTPException(status_code=400, detail="Disruption must contain at least one valid change record.")

        # Validate change types
        valid_types = {"faculty_unavailable", "room_unavailable", "add_faculty", "add_session", "remove_session"}
        for idx, ch in enumerate(changes):
            t = ch.get("type")
            if t not in valid_types:
                raise HTTPException(status_code=400, detail=f"Change #{idx+1} has invalid type '{t}'. Must be one of {valid_types}")
            if t == "faculty_unavailable" and not ch.get("faculty_id"):
                raise HTTPException(status_code=400, detail=f"Change #{idx+1} (faculty_unavailable) requires 'faculty_id'")
            if t == "room_unavailable" and not ch.get("room_id"):
                raise HTTPException(status_code=400, detail=f"Change #{idx+1} (room_unavailable) requires 'room_id'")
            if t == "add_session" and not ch.get("session"):
                raise HTTPException(status_code=400, detail=f"Change #{idx+1} (add_session) requires 'session' definition")
            if t == "remove_session" and not ch.get("session_id"):
                raise HTTPException(status_code=400, detail=f"Change #{idx+1} (remove_session) requires 'session_id'")

        dis_id = payload.get("id") or f"DIS-{int(datetime.now(timezone.utc).timestamp()*1000)}"
        title = payload.get("title") or f"Disruption Report ({dis_id})"
        description = payload.get("description", "Campus schedule disruption")
        dataset_id = payload.get("dataset_id", "cit-public-v1")
        now_iso = datetime.now(timezone.utc).isoformat()

        conn = get_connection()
        cur = conn.cursor()
        cur.execute("""
            INSERT OR REPLACE INTO disruptions (
                id, title, description, dataset_id, raw_json, changes_json,
                status, reported_by, reported_at
            ) VALUES (?, ?, ?, ?, ?, ?, 'reported', ?, ?)
        """, (
            dis_id,
            title,
            description,
            dataset_id,
            json.dumps(payload),
            json.dumps(changes),
            user.get("name", user.get("id", "admin")),
            now_iso
        ))

        cur.execute("""
            INSERT INTO rescheduling_audit_logs (disruption_id, user_id, user_role, action, details_json)
            VALUES (?, ?, ?, 'disruption_reported', ?)
        """, (dis_id, user.get("id", "user"), user_role, json.dumps({"title": title, "changes_count": len(changes)})))

        conn.commit()
        conn.close()

        return self.get_disruption_by_id(dis_id)

    def list_disruptions(self) -> List[Dict[str, Any]]:
        """Lists all disruption reports."""
        conn = get_connection()
        cur = conn.cursor()
        cur.execute("SELECT * FROM disruptions ORDER BY reported_at DESC")
        rows = cur.fetchall()
        conn.close()

        disruptions = []
        for r in rows:
            d = dict(r)
            d["changes"] = json.loads(d["changes_json"] or "[]")
            d["impact_summary"] = json.loads(d["impact_summary_json"] or "{}") if d.get("impact_summary_json") else None
            disruptions.append(d)
        return disruptions

    def get_disruption_by_id(self, disruption_id: str) -> Dict[str, Any]:
        """Retrieves a single disruption record."""
        conn = get_connection()
        cur = conn.cursor()
        cur.execute("SELECT * FROM disruptions WHERE id = ?", (disruption_id,))
        row = cur.fetchone()
        conn.close()
        if not row:
            raise HTTPException(status_code=404, detail=f"Disruption '{disruption_id}' not found")

        d = dict(row)
        d["changes"] = json.loads(d["changes_json"] or "[]")
        d["impact_summary"] = json.loads(d["impact_summary_json"] or "{}") if d.get("impact_summary_json") else None
        return d

    def analyze_impact(self, disruption_id: str) -> Dict[str, Any]:
        """Runs impact analysis for a specific disruption against the active timetable."""
        dis = self.get_disruption_by_id(disruption_id)
        active_id = TimetableVersionManager.get_active_timetable_id()
        active_assignments = TimetableVersionManager.get_version_assignments(active_id)

        # Fallback to baseline if active has 0 assignments
        if not active_assignments:
            active_assignments = TimetableVersionManager.get_version_assignments("baseline")

        # Load exams & bookings
        conn = get_connection()
        cur = conn.cursor()
        exams = []
        try:
            cur.execute("SELECT exam_id, day, session, rooms_json, groups_json FROM exam_schedules")
            for er in cur.fetchall():
                exams.append({
                    "exam_id": er["exam_id"],
                    "day": er["day"],
                    "session": er["session"],
                    "groups": json.loads(er["groups_json"] or "[]")
                })
        except Exception:
            exams = []

        cur.execute("SELECT id, assigned_room_id, assigned_day, status FROM booking_requests WHERE status = 'approved'")
        bookings = [dict(b) for b in cur.fetchall()]
        conn.close()

        impact = DisruptionImpactAnalyzer.analyze_impact(
            disruption_changes=dis["changes"],
            baseline_sessions=active_assignments,
            sessions_metadata=self.sessions_dict,
            exams=exams,
            bookings=bookings
        )
        impact["disruption_id"] = disruption_id

        # Update disruption record with impact summary
        conn = get_connection()
        cur = conn.cursor()
        cur.execute("""
            UPDATE disruptions
            SET impact_summary_json = ?,
                status = CASE WHEN status = 'reported' THEN 'analyzing' ELSE status END
            WHERE id = ?
        """, (json.dumps(impact), disruption_id))
        conn.commit()
        conn.close()

        return impact

    def generate_rescheduling_proposal(
        self,
        disruption_id: str,
        user: Dict[str, Any],
        time_limit_seconds: int = 45,
        target_version_name: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Executes CP-SAT minimal perturbation rescheduling and generates a proposal.
        Preserves baseline and does NOT overwrite active schedule automatically.
        """
        dis = self.get_disruption_by_id(disruption_id)
        active_id = TimetableVersionManager.get_active_timetable_id()
        active_assignments = TimetableVersionManager.get_version_assignments(active_id)
        if not active_assignments:
            active_assignments = TimetableVersionManager.get_version_assignments("baseline")

        baseline_sched = {
            "team": "CIT-DevOps",
            "dataset_id": dis.get("dataset_id", "cit-public-v1"),
            "sessions": active_assignments
        }

        # Format disruption payload for solver
        disruption_payload = {
            "id": dis["id"],
            "description": dis["description"],
            "changes": dis["changes"]
        }

        solver_res = TimetableReschedulingEngine.reschedule(
            dataset=self.dataset,
            baseline_schedule=baseline_sched,
            disruption_payload=disruption_payload,
            time_limit_seconds=time_limit_seconds
        )

        if not solver_res["success"]:
            raise HTTPException(
                status_code=400,
                detail=f"Rescheduling Infeasible: {solver_res.get('error', 'Constraint conflict prevents placement.')}"
            )

        # Unique proposal ID and target version ID
        conn = get_connection()
        cur = conn.cursor()
        cur.execute("SELECT COUNT(*) FROM rescheduling_proposals")
        prop_count = cur.fetchone()[0] + 1
        conn.close()

        proposal_id = f"PROP-{dis['id']}-v{prop_count}"
        target_ver_id = target_version_name or f"v{prop_count}_{dis['id']}"

        saved = ProposalManager.save_proposal(
            proposal_id=proposal_id,
            disruption_id=dis["id"],
            baseline_id=active_id,
            target_version_id=target_ver_id,
            solver_result=solver_res,
            user_id=user.get("id", "admin")
        )
        return saved

    def list_proposals(self, disruption_id: Optional[str] = None) -> List[Dict[str, Any]]:
        return ProposalManager.list_proposals(disruption_id)

    def get_proposal_by_id(self, proposal_id: str) -> Dict[str, Any]:
        return ProposalManager.get_proposal_by_id(proposal_id)

    def get_proposal_comparison(self, proposal_id: str) -> Dict[str, Any]:
        return ProposalManager.get_comparison(proposal_id)

    def approve_proposal(self, proposal_id: str, user: Dict[str, Any], reason: Optional[str] = None) -> Dict[str, Any]:
        return ProposalManager.approve_proposal(proposal_id, user, reason)

    def reject_proposal(self, proposal_id: str, user: Dict[str, Any], reason: Optional[str] = None) -> Dict[str, Any]:
        return ProposalManager.reject_proposal(proposal_id, user, reason)

    def get_timetable_versions(self) -> List[Dict[str, Any]]:
        return TimetableVersionManager.get_all_versions()
