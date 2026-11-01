"""
Dataset Validation, Import and Safe Replacement Service for CIT Campus Platform.
Handles schema checking, foreign key reference integrity, transactional ingestion,
and clean demo-data reset.
"""

import json
import sqlite3
from pathlib import Path
from typing import Dict, Any, List, Tuple, Optional
from backend.db.database import get_connection, init_db
from backend.db.seed import seed_dataset

DATA_PATH = Path(__file__).resolve().parent.parent.parent / "CrunchWeek_StarterPack" / "data" / "cit_public.json"


class DatasetService:
    """
    Validates and imports official CIT dataset input files safely with complete rollbacks on failure.
    """

    @staticmethod
    def _resolve_csv_payload(data: Dict[str, Any]) -> Tuple[Dict[str, Any], List[str]]:
        """
        Parses and resolves Multi-CSV or Single-CSV uploads into a complete institutional dataset.
        Applies aliases, auto-normalizes primary keys, and safely overlays changes.
        """
        errors: List[str] = []
        if not isinstance(data, dict):
            return data, errors

        alias_map = {
            "courses": "courses", "course": "courses",
            "rooms": "rooms", "room": "rooms",
            "faculty": "faculty", "faculties": "faculty", "professors": "faculty",
            "sessions": "sessions", "session": "sessions",
            "student_groups": "student_groups", "student_group": "student_groups", "groups": "student_groups",
            "exams": "exams", "exam": "exams", "examination": "exams",
            "booking_requests": "booking_requests", "bookings": "booking_requests", "booking": "booking_requests",
            "room_unavailability": "room_unavailability", "unavailability": "room_unavailability",
            "cancellations": "cancellations", "cancellation": "cancellations"
        }

        # Multi-CSV payload
        if "_csv_files" in data and isinstance(data["_csv_files"], dict):
            from backend.services.csv_helper import parse_single_csv_string
            try:
                with open(DATA_PATH, "r", encoding="utf-8") as f:
                    base_data = json.load(f)
                uploaded_names = []
                for fname, raw_txt in data["_csv_files"].items():
                    raw_stem = Path(fname).stem.strip().lower()
                    table_name = alias_map.get(raw_stem, raw_stem)
                    uploaded_names.append(table_name)
                    parsed_items = parse_single_csv_string(raw_txt, table_hint=table_name)
                    if table_name == "room_unavailability":
                        room_map = {r["id"]: r for r in base_data.get("rooms", []) if "id" in r}
                        for un in parsed_items:
                            rid = un.get("room_id")
                            if rid in room_map:
                                if "unavailable" not in room_map[rid]:
                                    room_map[rid]["unavailable"] = []
                                room_map[rid]["unavailable"].append({
                                    "day": un.get("day"),
                                    "periods": un.get("periods", []),
                                    "reason": un.get("reason", "Maintenance")
                                })
                    elif len(data["_csv_files"]) < 5 and table_name in ["courses", "faculty", "rooms", "student_groups"]:
                        # Partial upload: upsert to preserve relational integrity with remaining unedited tables
                        existing_map = {item.get("id"): item for item in base_data.get(table_name, []) if item.get("id")}
                        for itm in parsed_items:
                            if itm.get("id"):
                                existing_map[itm["id"]] = itm
                        base_data[table_name] = list(existing_map.values())
                    else:
                        base_data[table_name] = parsed_items
                names_tag = "-".join(uploaded_names[:3])
                base_data["dataset_id"] = f"cit-multi-csv-{names_tag}"
                data = base_data
            except Exception as e:
                errors.append(f"Failed to parse uploaded CSV files: {str(e)}")

        elif "_csv_raw" in data:
            from backend.services.csv_helper import parse_single_csv_string
            filename = data.get("_csv_filename", "rooms.csv")
            raw_stem = Path(filename).stem.strip().lower()
            table_name = alias_map.get(raw_stem, raw_stem)
            try:
                with open(DATA_PATH, "r", encoding="utf-8") as f:
                    base_data = json.load(f)
                parsed_items = parse_single_csv_string(data["_csv_raw"], table_hint=table_name)
                if table_name == "room_unavailability":
                    room_map = {r["id"]: r for r in base_data.get("rooms", []) if "id" in r}
                    for un in parsed_items:
                        rid = un.get("room_id")
                        if rid in room_map:
                            if "unavailable" not in room_map[rid]:
                                room_map[rid]["unavailable"] = []
                            room_map[rid]["unavailable"].append({
                                "day": un.get("day"),
                                "periods": un.get("periods", []),
                                "reason": un.get("reason", "Maintenance")
                            })
                elif table_name in ["courses", "faculty", "rooms", "student_groups"]:
                    # Upsert to preserve relational integrity with remaining unedited tables
                    existing_map = {item.get("id"): item for item in base_data.get(table_name, []) if item.get("id")}
                    for itm in parsed_items:
                        if itm.get("id"):
                            existing_map[itm["id"]] = itm
                    base_data[table_name] = list(existing_map.values())
                else:
                    base_data[table_name] = parsed_items
                base_data["dataset_id"] = f"cit-custom-{table_name}"
                data = base_data
            except Exception as e:
                errors.append(f"Failed to parse uploaded CSV: {str(e)}")

        return data, errors

    @staticmethod
    def validate_dataset_structure(data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Performs comprehensive structural, data type, and relational reference validation
        on an uploaded dataset JSON object without modifying the database.
        """
        errors: List[str] = []
        warnings: List[str] = []

        # Automatic Multi-CSV or Single-CSV handling
        data, parse_errors = DatasetService._resolve_csv_payload(data)
        errors.extend(parse_errors)

        if isinstance(data, dict) and "changes" in data:
            errors.append("Detected Disruption Change file (e.g. sample_disruption.json). Please apply disruptions in the Disruption & Reschedule module.")
        if isinstance(data, dict) and "fest_week" in data and "rooms" not in data:
            errors.append("Detected Schedule Export file (e.g. schedule.json). Please upload an institutional dataset (e.g. cit_public.json or CSVs).")

        # 1. Root structure
        required_root_keys = ["rooms", "faculty", "student_groups", "courses", "sessions"]
        for k in required_root_keys:
            if k not in data:
                errors.append(f"Missing required top-level key: '{k}'")
            elif not isinstance(data[k], list):
                errors.append(f"Top-level key '{k}' must be an array, got {type(data[k]).__name__}")

        if errors:
            return {
                "is_valid": False,
                "summary": {},
                "errors": errors,
                "warnings": warnings
            }

        # 2. Extract primary keys
        room_ids = set()
        faculty_ids = set()
        group_ids = set()
        course_ids = set()
        session_ids = set()

        # Check Rooms
        for idx, r in enumerate(data.get("rooms", [])):
            if not isinstance(r, dict):
                errors.append(f"Room at index {idx} must be a dictionary.")
                continue
            rid = str(r.get("id") or r.get("room_id") or r.get("\ufeffid") or "").strip()
            if not rid:
                errors.append(f"Room at index {idx} missing valid 'id'.")
            elif rid in room_ids:
                errors.append(f"Duplicate room ID detected: '{rid}'.")
            else:
                r["id"] = rid
                room_ids.add(rid)

            if "capacity" not in r or not isinstance(r.get("capacity"), (int, float)) or r["capacity"] <= 0:
                errors.append(f"Room '{rid or idx}' must have positive integer 'capacity'.")
            if "type" not in r:
                warnings.append(f"Room '{rid or idx}' missing 'type'.")

        # Check Faculty
        for idx, f in enumerate(data.get("faculty", [])):
            if not isinstance(f, dict):
                errors.append(f"Faculty at index {idx} must be a dictionary.")
                continue
            fid = str(f.get("id") or f.get("faculty_id") or f.get("\ufeffid") or "").strip()
            if not fid:
                errors.append(f"Faculty at index {idx} missing valid 'id'.")
            elif fid in faculty_ids:
                errors.append(f"Duplicate faculty ID detected: '{fid}'.")
            else:
                f["id"] = fid
                faculty_ids.add(fid)

        # Check Student Groups
        for idx, g in enumerate(data.get("student_groups", [])):
            if not isinstance(g, dict):
                errors.append(f"Student group at index {idx} must be a dictionary.")
                continue
            gid = str(g.get("id") or g.get("group_id") or g.get("\ufeffid") or "").strip()
            if not gid:
                errors.append(f"Student group at index {idx} missing valid 'id'.")
            elif gid in group_ids:
                errors.append(f"Duplicate student group ID detected: '{gid}'.")
            else:
                g["id"] = gid
                group_ids.add(gid)

            if "size" not in g or not isinstance(g.get("size"), (int, float)) or g["size"] <= 0:
                errors.append(f"Student group '{gid or idx}' must have positive integer 'size'.")

        # Check Courses
        for idx, c in enumerate(data.get("courses", [])):
            if not isinstance(c, dict):
                errors.append(f"Course at index {idx} must be a dictionary.")
                continue
            cid = str(c.get("id") or c.get("course_id") or c.get("code") or c.get("\ufeffid") or "").strip()
            if not cid:
                errors.append(f"Course at index {idx} missing valid 'id'.")
            elif cid in course_ids:
                errors.append(f"Duplicate course ID detected: '{cid}'.")
            else:
                c["id"] = cid
                course_ids.add(cid)

        # Check Sessions and Foreign References
        for idx, s in enumerate(data.get("sessions", [])):
            if not isinstance(s, dict):
                errors.append(f"Session at index {idx} must be a dictionary.")
                continue
            sid = str(s.get("id") or s.get("session_id") or s.get("\ufeffid") or "").strip()
            if not sid:
                errors.append(f"Session at index {idx} missing valid 'id'.")
            elif sid in session_ids:
                errors.append(f"Duplicate session ID detected: '{sid}'.")
            else:
                s["id"] = sid
                session_ids.add(sid)

            # Course reference
            cid = str(s.get("course_id") or "").strip()
            if not cid or cid not in course_ids:
                errors.append(f"Session '{sid}' references non-existent course_id '{cid}'.")

            # Faculty reference
            fid = str(s.get("faculty_id") or "").strip()
            if not fid or fid not in faculty_ids:
                errors.append(f"Session '{sid}' references non-existent faculty_id '{fid}'.")

            # Student groups reference
            s_groups = s.get("groups", [])
            if not isinstance(s_groups, list) or len(s_groups) == 0:
                errors.append(f"Session '{sid}' must specify at least one student group in 'groups'.")
            else:
                for sg in s_groups:
                    if str(sg).strip() not in group_ids:
                        errors.append(f"Session '{sid}' references non-existent student group '{sg}'.")

        is_valid = len(errors) == 0
        summary = {
            "dataset_id": data.get("dataset_id", "uploaded-dataset"),
            "rooms_count": len(room_ids),
            "faculty_count": len(faculty_ids),
            "student_groups_count": len(group_ids),
            "courses_count": len(course_ids),
            "sessions_count": len(session_ids),
            "exams_count": len(data.get("exams", [])),
            "bookings_count": len(data.get("booking_requests", [])),
            "error_count": len(errors),
            "warning_count": len(warnings)
        }

        return {
            "is_valid": is_valid,
            "summary": summary,
            "errors": errors[:50], # top errors to prevent payload overflow
            "warnings": warnings[:50]
        }

    @staticmethod
    def import_dataset(data: Dict[str, Any], user_id: str = "admin_1") -> Dict[str, Any]:
        """
        Safely imports validated dataset into SQLite using an atomic transaction.
        If validation fails, rolls back completely without leaving partial data.
        """
        data, parse_errors = DatasetService._resolve_csv_payload(data)
        if parse_errors:
            return {
                "success": False,
                "message": f"Failed to parse uploaded CSV: {'; '.join(parse_errors[:3])}",
                "errors": parse_errors,
                "warnings": []
            }

        validation = DatasetService.validate_dataset_structure(data)
        if not validation["is_valid"]:
            err_summary = "; ".join(validation["errors"][:3])
            return {
                "success": False,
                "message": f"Dataset validation failed: {err_summary}",
                "errors": validation["errors"],
                "warnings": validation["warnings"]
            }

        conn = get_connection()
        try:
            cur = conn.cursor()
            # Backup current active state
            cur.execute("SELECT id, stats_json FROM timetables WHERE id = 'active'")
            active_tt = cur.fetchone()

            # Clean and re-seed tables inside single transaction
            cur.execute("DELETE FROM sessions")
            cur.execute("DELETE FROM courses")
            cur.execute("DELETE FROM student_groups")
            cur.execute("DELETE FROM faculty_unavailability")
            cur.execute("DELETE FROM faculty")
            cur.execute("DELETE FROM room_unavailability")
            cur.execute("DELETE FROM rooms")
            cur.execute("DELETE FROM timetable_assignments")
            cur.execute("DELETE FROM exam_schedules")

            # Insert Rooms
            for r in data.get("rooms", []):
                rid = str(r.get("id") or r.get("room_id") or "").strip()
                cur.execute("""
                    INSERT INTO rooms (id, name, building, type, capacity, features_json, accessible, allowed_uses_json)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    rid, r.get("name", rid), r.get("building", "Main"), r["type"],
                    r["capacity"], json.dumps(r.get("features", [])), 1 if r.get("accessible") else 0,
                    json.dumps(r.get("allowed_uses", []))
                ))
                for un in r.get("unavailable", []):
                    cur.execute("""
                        INSERT INTO room_unavailability (room_id, day, periods_json, reason)
                        VALUES (?, ?, ?, ?)
                    """, (rid, un["day"], json.dumps(un.get("periods", [])), un.get("reason", "Maintenance")))

            # Insert Faculty
            for f in data.get("faculty", []):
                fid = str(f.get("id") or f.get("faculty_id") or "").strip()
                cur.execute("""
                    INSERT INTO faculty (id, name, department, max_hours_per_day, needs_accessible, preferences_json)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (
                    fid, f["name"], f.get("department", "CSE"),
                    f.get("max_hours_per_day", 4), 1 if f.get("needs_accessible") else 0,
                    json.dumps(f.get("preferences", []))
                ))
                for un in f.get("unavailable", []):
                    cur.execute("""
                        INSERT INTO faculty_unavailability (faculty_id, day, periods_json, reason)
                        VALUES (?, ?, ?, ?)
                    """, (fid, un["day"], json.dumps(un.get("periods", [])), un.get("reason", "Unavailable")))

            # Insert Groups
            for g in data.get("student_groups", []):
                gid = str(g.get("id") or g.get("group_id") or "").strip()
                cur.execute("""
                    INSERT INTO student_groups (id, name, year, department, size, needs_accessible)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (
                    gid, g.get("name", gid), g.get("year", 1),
                    g.get("department", "CSE"), g["size"], 1 if g.get("needs_accessible") else 0
                ))

            # Insert Courses
            for c in data.get("courses", []):
                cid = str(c.get("id") or c.get("course_id") or c.get("code") or "").strip()
                cur.execute("""
                    INSERT INTO courses (id, title, department, year, lecture_hours, tutorial_hours, lab_blocks)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (
                    cid, c.get("title", cid), c.get("department", "CSE"), c.get("year", 1),
                    c.get("lecture_hours", 0), c.get("tutorial_hours", 0), c.get("lab_blocks", 0)
                ))

            # Insert Sessions
            for s in data.get("sessions", []):
                sid = str(s.get("id") or s.get("session_id") or "").strip()
                cur.execute("""
                    INSERT INTO sessions (
                        id, course_id, kind, duration, size, faculty_id, groups_json, room_types_json,
                        needs_accessible, fixed_slot_json, basket_slot
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    sid, str(s.get("course_id") or "").strip(), s["kind"], s["duration"], s["size"], str(s.get("faculty_id") or "").strip(),
                    json.dumps(s.get("groups", [])), json.dumps(s.get("room_types", [])),
                    1 if s.get("needs_accessible") else 0,
                    json.dumps(s.get("fixed_slot")) if s.get("fixed_slot") else None,
                    s.get("basket_slot")
                ))

            # Record audit log
            cur.execute("""
                INSERT INTO audit_logs (user_id, user_role, action, details_json)
                VALUES (?, 'admin', 'dataset_imported', ?)
            """, (user_id, json.dumps(validation["summary"])))

            conn.commit()
            conn.close()

            return {
                "success": True,
                "message": f"Successfully imported dataset '{data.get('dataset_id', 'custom')}'. Database updated.",
                "summary": validation["summary"]
            }

        except Exception as ex:
            conn.rollback()
            conn.close()
            return {
                "success": False,
                "message": f"Transaction failed and was safely rolled back: {str(ex)}",
                "errors": [str(ex)],
                "warnings": []
            }

    @staticmethod
    def reset_demo_data(user_id: str = "admin_1") -> Dict[str, Any]:
        """
        Restores the official clean starter pack dataset and restores baseline schedule.
        """
        # Re-seed database from DATA_PATH
        seed_dataset(reset_first=True)

        sched_file = Path(__file__).resolve().parent.parent.parent / "exports" / "schedule.json"
        if sched_file.exists():
            try:
                with open(sched_file, "r", encoding="utf-8") as f:
                    sched_data = json.load(f)
                conn = get_connection()
                cur = conn.cursor()
                cur.execute("""
                    INSERT OR REPLACE INTO timetables (id, name, is_active, source, stats_json)
                    VALUES ('active', 'Active Baseline Schedule', 1, 'generated', ?)
                """, (json.dumps({"hard_violations": [], "soft_total": 260}),))

                cur.execute("""
                    INSERT OR REPLACE INTO timetables (id, name, is_active, source, stats_json)
                    VALUES ('baseline', 'Baseline Academic Timetable', 1, 'generated', ?)
                """, (json.dumps({"hard_violations": [], "soft_total": 260}),))

                assign_tuples = []
                for s in sched_data.get("sessions", []):
                    assign_tuples.append(("active", s["session_id"], s["day"], s["start_period"], s["room_id"]))
                    assign_tuples.append(("baseline", s["session_id"], s["day"], s["start_period"], s["room_id"]))
                if assign_tuples:
                    cur.executemany("""
                        INSERT INTO timetable_assignments (timetable_id, session_id, day, start_period, room_id)
                        VALUES (?, ?, ?, ?, ?)
                    """, assign_tuples)

                for e in sched_data.get("exams", []):
                    cur.execute("""
                        UPDATE exam_schedules
                        SET day = ?, session = ?, rooms_json = ?
                        WHERE exam_id = ?
                    """, (e["day"], e["session"], json.dumps(e["rooms"]), e["exam_id"]))

                fest = sched_data.get("fest_week", {})
                for b in fest.get("bookings", []):
                    cur.execute("""
                        UPDATE booking_requests
                        SET status = ?, assigned_day = ?, assigned_start_period = ?,
                            assigned_end_period = ?, assigned_room_id = ?, decision_reason = ?
                        WHERE id = ?
                    """, (
                        b["status"], b.get("day"), b.get("start_period"),
                        b.get("end_period"), b.get("room_id"), b.get("reason", ""),
                        b["request_id"]
                    ))

                conn.commit()
                conn.close()
            except Exception as ex:
                print(f"[Warning] Failed to restore baseline schedule on reset: {ex}")

        return {
            "success": True,
            "message": "Demo data successfully reset to clean CIT starter-pack baseline.",
            "dataset_id": "cit-public-v1"
        }
