import json
from pathlib import Path
from backend.db.database import get_connection, init_db

DEFAULT_DATASET_PATH = Path(__file__).resolve().parent.parent.parent / "CrunchWeek_StarterPack" / "data" / "cit_public.json"

def calculate_effective_category(priority_order, role_cap_dict, role, requested_cat):
    cap = role_cap_dict.get(role, "club_event")
    req_idx = priority_order.index(requested_cat) if requested_cat in priority_order else len(priority_order) - 1
    cap_idx = priority_order.index(cap) if cap in priority_order else len(priority_order) - 1
    # effective category cannot be higher priority (smaller index) than the cap
    eff_idx = max(req_idx, cap_idx)
    return priority_order[eff_idx]

def seed_dataset(json_path: Path = DEFAULT_DATASET_PATH, reset_first: bool = True):
    if not json_path.exists():
        raise FileNotFoundError(f"Dataset not found at {json_path}")

    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    init_db(force_reset=reset_first)
    conn = get_connection()
    cur = conn.cursor()

    priority_order = data["priority_order"]
    role_category_cap = data["role_category_cap"]

    # 1. System Metadata
    meta_entries = [
        ("dataset_id", data["dataset_id"]),
        ("institute", data.get("institute", "Chilika Institute of Technology")),
        ("priority_order", json.dumps(priority_order)),
        ("role_category_cap", json.dumps(role_category_cap)),
        ("calendar", json.dumps(data["calendar"])),
    ]
    cur.executemany("INSERT OR REPLACE INTO system_meta (key, value) VALUES (?, ?)", meta_entries)

    # 2. Rooms & Room Unavailability
    rooms_data = []
    room_unavail_data = []
    for r in data["rooms"]:
        rooms_data.append((
            r["id"],
            r["name"],
            r["building"],
            r["type"],
            r["capacity"],
            json.dumps(r.get("features", [])),
            1 if r.get("accessible") else 0,
            json.dumps(r.get("allowed_uses", []))
        ))

    cur.executemany("""
        INSERT INTO rooms (id, name, building, type, capacity, features_json, accessible, allowed_uses_json)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, rooms_data)

    for u in data.get("room_unavailability", []):
        room_unavail_data.append((
            u["room_id"],
            u["day"],
            json.dumps(u["periods"]),
            u.get("reason", "")
        ))

    cur.executemany("""
        INSERT INTO room_unavailability (room_id, day, periods_json, reason)
        VALUES (?, ?, ?, ?)
    """, room_unavail_data)

    # 3. Faculty & Faculty Unavailability
    faculty_data = []
    faculty_unavail_data = []
    for f in data["faculty"]:
        faculty_data.append((
            f["id"],
            f["name"],
            f["department"],
            f.get("max_hours_per_day", 4),
            1 if f.get("needs_accessible") else 0,
            json.dumps(f.get("preferences", []))
        ))
        for u in f.get("unavailable", []):
            faculty_unavail_data.append((
                f["id"],
                u["day"],
                json.dumps(u["periods"]),
                u.get("reason", "")
            ))

    cur.executemany("""
        INSERT INTO faculty (id, name, department, max_hours_per_day, needs_accessible, preferences_json)
        VALUES (?, ?, ?, ?, ?, ?)
    """, faculty_data)

    cur.executemany("""
        INSERT INTO faculty_unavailability (faculty_id, day, periods_json, reason)
        VALUES (?, ?, ?, ?)
    """, faculty_unavail_data)

    # 4. Student Groups
    groups_data = [
        (g["id"], g["name"], g["year"], g.get("department", "COMMON"), g["size"], 1 if g.get("needs_accessible") else 0)
        for g in data["student_groups"]
    ]
    cur.executemany("""
        INSERT INTO student_groups (id, name, year, department, size, needs_accessible)
        VALUES (?, ?, ?, ?, ?, ?)
    """, groups_data)

    # 5. Courses
    courses_data = [
        (c["id"], c.get("title", c["id"]), c["department"], c.get("year"), c.get("lecture_hours", 0), c.get("tutorial_hours", 0), c.get("lab_blocks", 0))
        for c in data["courses"]
    ]
    cur.executemany("""
        INSERT INTO courses (id, title, department, year, lecture_hours, tutorial_hours, lab_blocks)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, courses_data)

    # 6. Sessions
    sessions_data = []
    for s in data["sessions"]:
        fixed_slot_json = json.dumps(s["fixed_slot"]) if "fixed_slot" in s else None
        sessions_data.append((
            s["id"],
            s["course_id"],
            s["kind"],
            s["duration"],
            s["size"],
            s["faculty_id"],
            json.dumps(s.get("groups", [])),
            json.dumps(s.get("room_types", [])),
            1 if s.get("needs_accessible") else 0,
            fixed_slot_json,
            s.get("basket_slot")
        ))
    cur.executemany("""
        INSERT INTO sessions (id, course_id, kind, duration, size, faculty_id, groups_json, room_types_json, needs_accessible, fixed_slot_json, basket_slot)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, sessions_data)

    # 7. Cancellations
    cancelled_ids = {c["request_id"] for c in data.get("cancellations", [])}

    # 8. Booking Requests
    bookings_data = []
    for b in data.get("booking_requests", []):
        eff_cat = calculate_effective_category(priority_order, role_category_cap, b["role"], b["requested_category"])
        status = "cancelled" if b["id"] in cancelled_ids else "pending"
        bookings_data.append((
            b["id"],
            b.get("raw_text", ""),
            b["role"],
            b["requested_category"],
            eff_cat,
            b["attendance"],
            b["duration_periods"],
            json.dumps(b.get("room_types", [])),
            json.dumps(b.get("windows", [])),
            json.dumps(b.get("needs", [])),
            json.dumps(b.get("mandatory_for_groups", [])),
            status,
            b["submitted_at"]
        ))

    cur.executemany("""
        INSERT INTO booking_requests (
            id, raw_text, role, requested_category, effective_category,
            attendance, duration_periods, room_types_json, windows_json,
            needs_json, mandatory_for_groups_json, status, submitted_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, bookings_data)

    # 9. Exams
    exams_data = []
    for e in data.get("exams", []):
        exams_data.append((
            e["id"],
            json.dumps(e.get("course_ids", [])),
            None, # Day to be scheduled
            None, # Session to be scheduled
            json.dumps([]), # Rooms to be scheduled
            json.dumps(e.get("groups", [])),
            e["size"],
            e.get("duration_hours", 2)
        ))
    cur.executemany("""
        INSERT INTO exam_schedules (exam_id, course_ids_json, day, session, rooms_json, groups_json, size, duration_hours)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, exams_data)

    conn.commit()
    conn.close()
    print(f"Successfully seeded database with {len(rooms_data)} rooms, {len(faculty_data)} faculty, {len(sessions_data)} sessions, {len(bookings_data)} bookings, {len(exams_data)} exams.")

if __name__ == "__main__":
    seed_dataset()
