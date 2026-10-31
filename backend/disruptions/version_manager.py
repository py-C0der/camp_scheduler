"""
Timetable Version and Revision Manager.
Maintains an immutable historical ledger of timetable versions.
Ensures atomic transitions between baseline and rescheduled versions without data loss.
"""

import json
from datetime import datetime
from typing import Dict, Any, List, Optional
from backend.db.database import get_connection


class TimetableVersionManager:
    """Manages multi-version timetables and historical snapshots."""

    @staticmethod
    def get_all_versions() -> List[Dict[str, Any]]:
        """Lists all timetable versions with session counts and modification metrics."""
        conn = get_connection()
        cur = conn.cursor()

        cur.execute("""
            SELECT t.id, t.name, t.is_active, t.source, t.stats_json, t.created_at,
                   COUNT(ta.session_id) as session_count
            FROM timetables t
            LEFT JOIN timetable_assignments ta ON t.id = ta.timetable_id
            GROUP BY t.id
            ORDER BY t.created_at ASC
        """)
        rows = cur.fetchall()

        # Load baseline assignments for movement comparison
        cur.execute("SELECT session_id, day, start_period, room_id FROM timetable_assignments WHERE timetable_id = 'baseline'")
        base_map = {r["session_id"]: (r["day"], r["start_period"], r["room_id"]) for r in cur.fetchall()}

        versions = []
        for r in rows:
            v_id = r["id"]
            # Count moved sessions relative to baseline
            cur.execute("SELECT session_id, day, start_period, room_id FROM timetable_assignments WHERE timetable_id = ?", (v_id,))
            v_assigns = cur.fetchall()
            moved_from_base = 0
            for a in v_assigns:
                sid = a["session_id"]
                if sid in base_map and (a["day"], a["start_period"], a["room_id"]) != base_map[sid]:
                    moved_from_base += 1

            versions.append({
                "id": v_id,
                "name": r["name"],
                "is_active": bool(r["is_active"]),
                "source": r["source"],
                "created_at": str(r["created_at"]),
                "sessions_count": r["session_count"],
                "sessions_moved_from_baseline": moved_from_base
            })

        conn.close()
        return versions

    @staticmethod
    def get_active_timetable_id() -> str:
        """Returns the currently active timetable version ID."""
        conn = get_connection()
        cur = conn.cursor()
        cur.execute("SELECT id FROM timetables WHERE is_active = 1 LIMIT 1")
        row = cur.fetchone()
        conn.close()
        return row["id"] if row else "baseline"

    @staticmethod
    def get_version_assignments(version_id: str) -> List[Dict[str, Any]]:
        """Retrieves session assignments for a specific timetable version."""
        conn = get_connection()
        cur = conn.cursor()
        cur.execute("""
            SELECT session_id, day, start_period, room_id
            FROM timetable_assignments
            WHERE timetable_id = ?
            ORDER BY session_id ASC
        """, (version_id,))
        rows = cur.fetchall()
        conn.close()
        return [dict(r) for r in rows]

    @staticmethod
    def activate_new_version(
        version_id: str,
        name: str,
        assignments: List[Dict[str, Any]],
        source: str = "disruption_reschedule",
        stats: Optional[Dict[str, Any]] = None
    ):
        """
        Atomically registers and activates a new timetable version.
        Marks previous active version as inactive without deleting it.
        """
        conn = get_connection()
        cur = conn.cursor()

        # 1. Mark existing versions as inactive
        cur.execute("UPDATE timetables SET is_active = 0")

        # 2. Insert or replace new version in timetables
        cur.execute("""
            INSERT OR REPLACE INTO timetables (id, name, is_active, source, stats_json)
            VALUES (?, ?, 1, ?, ?)
        """, (version_id, name, source, json.dumps(stats or {})))

        # 3. Insert assignments for new version
        cur.execute("DELETE FROM timetable_assignments WHERE timetable_id = ?", (version_id,))
        assign_tuples = [
            (version_id, s["session_id"], s["day"], s["start_period"], s["room_id"])
            for s in assignments
        ]
        cur.executemany("""
            INSERT INTO timetable_assignments (timetable_id, session_id, day, start_period, room_id)
            VALUES (?, ?, ?, ?, ?)
        """, assign_tuples)

        # 4. Also keep 'active' alias synchronized for backwards compatibility
        cur.execute("DELETE FROM timetable_assignments WHERE timetable_id = 'active'")
        active_tuples = [
            ("active", s["session_id"], s["day"], s["start_period"], s["room_id"])
            for s in assignments
        ]
        cur.executemany("""
            INSERT INTO timetable_assignments (timetable_id, session_id, day, start_period, room_id)
            VALUES (?, ?, ?, ?, ?)
        """, active_tuples)

        conn.commit()
        conn.close()
