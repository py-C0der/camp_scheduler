import sqlite3
import json
import os
from pathlib import Path
from typing import Dict, Any, List, Optional

DB_DIR = Path(__file__).resolve().parent.parent / "data_store"
DB_PATH = DB_DIR / "cit_campus.db"

def get_connection() -> sqlite3.Connection:
    DB_DIR.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    conn.execute("PRAGMA journal_mode = WAL;")
    return conn

def init_db(force_reset: bool = False):
    conn = get_connection()
    cur = conn.cursor()

    if force_reset:
        cur.executescript("""
            DROP TABLE IF EXISTS audit_logs;
            DROP TABLE IF EXISTS disruptions;
            DROP TABLE IF EXISTS exam_schedules;
            DROP TABLE IF EXISTS booking_decisions;
            DROP TABLE IF EXISTS fest_overrides;
            DROP TABLE IF EXISTS booking_requests;
            DROP TABLE IF EXISTS timetable_assignments;
            DROP TABLE IF EXISTS timetables;
            DROP TABLE IF EXISTS sessions;
            DROP TABLE IF EXISTS courses;
            DROP TABLE IF EXISTS student_groups;
            DROP TABLE IF EXISTS faculty_unavailability;
            DROP TABLE IF EXISTS faculty;
            DROP TABLE IF EXISTS room_unavailability;
            DROP TABLE IF EXISTS rooms;
            DROP TABLE IF EXISTS users;
            DROP TABLE IF EXISTS system_meta;
        """)

    cur.executescript("""
        CREATE TABLE IF NOT EXISTS system_meta (
            key TEXT PRIMARY KEY,
            value TEXT,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS users (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            email TEXT UNIQUE NOT NULL,
            role TEXT NOT NULL, -- 'admin', 'dept_coordinator', 'faculty', 'club_rep'
            department TEXT,
            faculty_id TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS rooms (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            building TEXT NOT NULL,
            type TEXT NOT NULL,
            capacity INTEGER NOT NULL,
            features_json TEXT NOT NULL, -- JSON array
            accessible INTEGER NOT NULL, -- 0 or 1
            allowed_uses_json TEXT NOT NULL -- JSON array
        );

        CREATE TABLE IF NOT EXISTS room_unavailability (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            room_id TEXT NOT NULL,
            day TEXT NOT NULL,
            periods_json TEXT NOT NULL, -- JSON array
            reason TEXT,
            FOREIGN KEY (room_id) REFERENCES rooms(id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS faculty (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            department TEXT NOT NULL,
            max_hours_per_day INTEGER NOT NULL DEFAULT 4,
            needs_accessible INTEGER NOT NULL DEFAULT 0,
            preferences_json TEXT -- JSON array
        );

        CREATE TABLE IF NOT EXISTS faculty_unavailability (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            faculty_id TEXT NOT NULL,
            day TEXT NOT NULL,
            periods_json TEXT NOT NULL, -- JSON array
            reason TEXT,
            FOREIGN KEY (faculty_id) REFERENCES faculty(id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS student_groups (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            year INTEGER NOT NULL,
            department TEXT NOT NULL,
            size INTEGER NOT NULL,
            needs_accessible INTEGER NOT NULL DEFAULT 0
        );

        CREATE TABLE IF NOT EXISTS courses (
            id TEXT PRIMARY KEY,
            title TEXT NOT NULL,
            department TEXT NOT NULL,
            year INTEGER,
            lecture_hours INTEGER DEFAULT 0,
            tutorial_hours INTEGER DEFAULT 0,
            lab_blocks INTEGER DEFAULT 0
        );

        CREATE TABLE IF NOT EXISTS sessions (
            id TEXT PRIMARY KEY,
            course_id TEXT NOT NULL,
            kind TEXT NOT NULL, -- 'lecture', 'tutorial', 'lab'
            duration INTEGER NOT NULL,
            size INTEGER NOT NULL,
            faculty_id TEXT NOT NULL,
            groups_json TEXT NOT NULL, -- JSON array
            room_types_json TEXT NOT NULL, -- JSON array
            needs_accessible INTEGER NOT NULL DEFAULT 0,
            fixed_slot_json TEXT, -- Optional JSON {day, start_period}
            basket_slot TEXT,
            FOREIGN KEY (faculty_id) REFERENCES faculty(id)
        );

        CREATE TABLE IF NOT EXISTS timetables (
            id TEXT PRIMARY KEY, -- 'baseline', 'active', 'rescheduled', etc.
            name TEXT NOT NULL,
            is_active INTEGER NOT NULL DEFAULT 0,
            source TEXT NOT NULL, -- 'generated', 'disruption_fix', 'imported'
            stats_json TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS timetable_assignments (
            timetable_id TEXT NOT NULL,
            session_id TEXT NOT NULL,
            day TEXT NOT NULL,
            start_period INTEGER NOT NULL,
            room_id TEXT NOT NULL,
            PRIMARY KEY (timetable_id, session_id),
            FOREIGN KEY (timetable_id) REFERENCES timetables(id) ON DELETE CASCADE,
            FOREIGN KEY (session_id) REFERENCES sessions(id) ON DELETE CASCADE,
            FOREIGN KEY (room_id) REFERENCES rooms(id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS booking_requests (
            id TEXT PRIMARY KEY,
            raw_text TEXT,
            role TEXT NOT NULL,
            requested_category TEXT NOT NULL,
            effective_category TEXT NOT NULL,
            attendance INTEGER NOT NULL,
            duration_periods INTEGER NOT NULL,
            room_types_json TEXT NOT NULL,
            windows_json TEXT NOT NULL,
            needs_json TEXT NOT NULL,
            mandatory_for_groups_json TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'pending', -- 'pending', 'approved', 'rejected', 'alternative_offered', 'cancelled'
            submitted_at TEXT NOT NULL,
            created_by TEXT,
            assigned_room_id TEXT,
            assigned_day TEXT,
            assigned_start_period INTEGER,
            assigned_end_period INTEGER,
            decision_reason TEXT,
            decision_by TEXT,
            decision_at TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS fest_overrides (
            session_id TEXT NOT NULL,
            day TEXT NOT NULL,
            start_period INTEGER NOT NULL,
            room_id TEXT NOT NULL,
            displaced_by TEXT NOT NULL,
            PRIMARY KEY (session_id, displaced_by)
        );

        CREATE TABLE IF NOT EXISTS exam_schedules (
            exam_id TEXT PRIMARY KEY,
            course_ids_json TEXT NOT NULL,
            day TEXT,
            session TEXT, -- 'AM', 'PM'
            rooms_json TEXT NOT NULL, -- JSON array
            groups_json TEXT NOT NULL,
            size INTEGER NOT NULL,
            duration_hours INTEGER NOT NULL DEFAULT 2
        );

        CREATE TABLE IF NOT EXISTS exam_schedule_versions (
            id TEXT PRIMARY KEY,
            version_number INTEGER NOT NULL,
            status TEXT NOT NULL DEFAULT 'proposed', -- 'proposed', 'approved', 'archived'
            is_active INTEGER NOT NULL DEFAULT 0,
            solver_status TEXT NOT NULL,
            solve_time_seconds REAL DEFAULT 0,
            soft_penalty INTEGER DEFAULT 0,
            created_by TEXT DEFAULT 'admin',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS exam_assignments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            version_id TEXT NOT NULL,
            exam_id TEXT NOT NULL,
            day TEXT NOT NULL,
            session TEXT NOT NULL,
            rooms_json TEXT NOT NULL,
            total_effective_seats INTEGER NOT NULL,
            is_multi_room INTEGER NOT NULL DEFAULT 0,
            FOREIGN KEY (version_id) REFERENCES exam_schedule_versions(id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS exam_validation_reports (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            version_id TEXT NOT NULL,
            is_valid INTEGER NOT NULL,
            hard_violation_count INTEGER NOT NULL DEFAULT 0,
            hard_violations_json TEXT,
            soft_penalty INTEGER NOT NULL DEFAULT 0,
            validated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (version_id) REFERENCES exam_schedule_versions(id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS exam_approvals (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            version_id TEXT NOT NULL,
            approved_by TEXT NOT NULL,
            approval_notes TEXT,
            approved_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (version_id) REFERENCES exam_schedule_versions(id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS disruptions (
            id TEXT PRIMARY KEY,
            description TEXT NOT NULL,
            raw_json TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'uploaded', -- 'uploaded', 'applied', 'reverted'
            changes_summary_json TEXT,
            sessions_moved INTEGER DEFAULT 0,
            applied_at TIMESTAMP,
            applied_by TEXT
        );

        CREATE TABLE IF NOT EXISTS audit_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT NOT NULL,
            user_role TEXT NOT NULL,
            action TEXT NOT NULL,
            details_json TEXT,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
    """)

    # Seed Demo Users if not present
    cur.execute("SELECT COUNT(*) FROM users")
    if cur.fetchone()[0] == 0:
        demo_users = [
            ("admin_1", "Dean Academics (Admin)", "admin@cit.ac.in", "admin", "Dean Office", None),
            ("coord_cse", "Dr. CSE Coordinator", "cse_coord@cit.ac.in", "dept_coordinator", "CSE", "F01"),
            ("fac_arvind", "Prof. Arvind Rao (Faculty)", "arvind@cit.ac.in", "faculty", "CSE", "F01"),
            ("club_tech", "Robotics Club Lead (Club Rep)", "techclub@cit.ac.in", "club_rep", "Student Affairs", None)
        ]
        cur.executemany("""
            INSERT INTO users (id, name, email, role, department, faculty_id)
            VALUES (?, ?, ?, ?, ?, ?)
        """, demo_users)

    conn.commit()
    conn.close()

if __name__ == "__main__":
    init_db(force_reset=True)
    print("Database initialized successfully at", DB_PATH)
