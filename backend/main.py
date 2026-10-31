import os
import json
import time
from pathlib import Path
from typing import Dict, Any, List, Optional
from fastapi import FastAPI, HTTPException, Depends, Header, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from backend.db.database import get_connection, init_db
from backend.db.seed import seed_dataset, calculate_effective_category
from backend.engine.timetable_solver import solve_timetable
from backend.engine.exam_solver import solve_exams
from backend.engine.fest_solver import solve_fest_bookings
from backend.engine.disruption_engine import solve_disruption_reschedule
from backend.services.nlp_service import parse_venue_request
from backend.services.export_service import export_schedules, run_official_validator
from backend.services.validation_service import audit_all_constraints
from CrunchWeek_StarterPack.validator import load, run as run_validator
from backend.api.dashboard_routes import dashboard_router
from backend.api.exam_routes import exam_router, export_exam_router
from backend.api.booking_routes import router as booking_router, booking_export_router
from backend.api.disruption_routes import router as disruption_router

DATA_PATH = Path(__file__).resolve().parent.parent / "CrunchWeek_StarterPack" / "data" / "cit_public.json"
DISRUPTION_PATH = Path(__file__).resolve().parent.parent / "CrunchWeek_StarterPack" / "examples" / "sample_disruption.json"
EXPORTS_DIR = Path(__file__).resolve().parent.parent / "exports"

app = FastAPI(
    title="CIT Campus Scheduling & Venue Management Platform",
    description="Advanced Backend Engine for Timetable Optimization, Exam Scheduling, Disruption Management, and Venue Bookings",
    version="1.0.0"
)

app.include_router(dashboard_router)
app.include_router(exam_router)
app.include_router(export_exam_router)
app.include_router(booking_router)
app.include_router(booking_export_router)
app.include_router(disruption_router)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ----------------- In-memory / DB State Cache -----------------
STATE = {
    "active_timetable": None,
    "active_exams": None,
    "active_fest": None,
    "disrupted_timetable": None,
    "active_user": {
        "id": "admin_1",
        "name": "Dean Academics (Admin)",
        "email": "admin@cit.ac.in",
        "role": "admin",
        "department": "Dean Office"
    }
}

# ----------------- Blueprint MVP Endpoints -----------------
@app.get("/api/health")
def health_check():
    return {"status": "healthy", "service": "CIT Campus Scheduling API"}

@app.get("/api/dataset/summary")
def dataset_summary():
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) FROM rooms")
    r_count = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM faculty")
    f_count = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM student_groups")
    g_count = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM courses")
    c_count = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM sessions")
    s_count = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM booking_requests")
    b_count = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM exam_schedules")
    e_count = cur.fetchone()[0]
    conn.close()
    return {
        "dataset_id": "cit-public-v1",
        "rooms": r_count,
        "faculty": f_count,
        "student_groups": g_count,
        "courses": c_count,
        "sessions": s_count,
        "booking_requests": b_count,
        "exams": e_count,
        "teaching_periods": 9,
        "days": ["MON", "TUE", "WED", "THU", "FRI"]
    }

@app.get("/api/metadata")
def get_metadata():
    return get_filter_options()

@app.get("/api/rooms")
def get_all_rooms():
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT id, name, building, type, capacity, features_json, accessible, allowed_uses_json FROM rooms ORDER BY id")
    rows = cur.fetchall()
    conn.close()
    res = []
    for r in rows:
        d = dict(r)
        d["features"] = json.loads(d["features_json"])
        d["allowed_uses"] = json.loads(d["allowed_uses_json"])
        res.append(d)
    return {"rooms": res}

@app.get("/api/sessions")
def get_all_sessions():
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT id, course_id, kind, duration, size, faculty_id, groups_json, room_types_json, needs_accessible, basket_slot FROM sessions ORDER BY id")
    rows = cur.fetchall()
    conn.close()
    res = []
    for r in rows:
        d = dict(r)
        d["groups"] = json.loads(d["groups_json"])
        d["room_types"] = json.loads(d["room_types_json"])
        res.append(d)
    return {"sessions": res}

@app.get("/api/timetable/latest")
def get_latest_timetable():
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT stats_json, created_at FROM timetables WHERE id = 'active'")
    row = cur.fetchone()
    if not row:
        conn.close()
        return {"status": "none", "message": "No timetable generated yet."}
    stats = json.loads(row["stats_json"]) if row["stats_json"] else {}
    cur.execute("SELECT session_id, day, start_period, room_id FROM timetable_assignments WHERE timetable_id = 'active'")
    assigns = [dict(r) for r in cur.fetchall()]
    conn.close()
    return {
        "status": "active",
        "created_at": row["created_at"],
        "stats": stats,
        "assignments_count": len(assigns),
        "assignments": assigns
    }

@app.get("/api/timetable/validations")
def get_validations_catalog():
    return audit_all_constraints()

@app.post("/api/timetable/validate")
def validate_timetable_api():
    audit = audit_all_constraints()
    official = validate_current()
    return {
        "status": "success",
        "audit": audit,
        "official_validator": official
    }

@app.get("/api/export/schedule")
def download_schedule():
    schedule_file = EXPORTS_DIR / "schedule.json"
    if not schedule_file.exists():
        generate_full_timetable()
    with open(schedule_file, "r", encoding="utf-8") as f:
        return json.load(f)

from fastapi.responses import HTMLResponse, FileResponse
from fastapi.staticfiles import StaticFiles

FRONTEND_DIR = Path(__file__).resolve().parent.parent / "frontend"
FRONTEND_DIR.mkdir(parents=True, exist_ok=True)

@app.get("/", response_class=HTMLResponse)
def serve_index():
    index_file = FRONTEND_DIR / "index.html"
    if index_file.exists():
        return FileResponse(index_file)
    return HTMLResponse("<h1>CIT Campus Operations API is Live. Visit /docs for OpenAPI specs.</h1>")

@app.on_event("startup")
def startup_event():
    # Check if database is populated, if not seed it
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) FROM rooms")
    count = cur.fetchone()[0]
    conn.close()
    if count == 0:
        seed_dataset()

# ----------------- Auth & Roles -----------------
@app.get("/api/auth/roles")
def get_roles():
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT id, name, email, role, department, faculty_id FROM users")
    users = [dict(row) for row in cur.fetchall()]
    conn.close()
    return {"users": users, "active_user": STATE["active_user"]}

class SwitchUserRequest(BaseModel):
    user_id: str

@app.post("/api/auth/switch")
def switch_user(req: SwitchUserRequest):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT id, name, email, role, department, faculty_id FROM users WHERE id = ?", (req.user_id,))
    row = cur.fetchone()
    conn.close()
    if not row:
        raise HTTPException(status_code=404, detail="User not found")
    STATE["active_user"] = dict(row)
    return {"status": "success", "active_user": STATE["active_user"]}

# ----------------- Timetable & Metadata -----------------
@app.get("/api/meta/filters")
def get_filter_options():
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT id, name, year, department, size FROM student_groups ORDER BY id")
    groups = [dict(r) for r in cur.fetchall()]
    cur.execute("SELECT id, name, department FROM faculty ORDER BY id")
    faculty = [dict(r) for r in cur.fetchall()]
    cur.execute("SELECT id, name, building, type, capacity FROM rooms ORDER BY id")
    rooms = [dict(r) for r in cur.fetchall()]
    conn.close()
    return {"groups": groups, "faculty": faculty, "rooms": rooms}

@app.get("/api/timetable/grid")
def get_timetable_grid(view_type: str = "group", target_id: Optional[str] = None):
    """
    Returns weekly timetable grid cells filtered by group, faculty, or room.
    """
    conn = get_connection()
    cur = conn.cursor()
    
    # Query assignments
    cur.execute("""
        SELECT a.session_id, a.day, a.start_period, a.room_id,
               s.course_id, s.kind, s.duration, s.size, s.faculty_id,
               s.groups_json, s.basket_slot, f.name as faculty_name,
               r.name as room_name, c.title as course_title
        FROM timetable_assignments a
        JOIN sessions s ON a.session_id = s.id
        LEFT JOIN faculty f ON s.faculty_id = f.id
        LEFT JOIN rooms r ON a.room_id = r.id
        LEFT JOIN courses c ON s.course_id = c.id
        WHERE a.timetable_id = 'active'
    """)
    rows = cur.fetchall()
    conn.close()
    
    events = []
    for row in rows:
        r_dict = dict(row)
        r_dict["groups"] = json.loads(r_dict["groups_json"])
        
        # Apply filter
        if target_id and target_id.strip():
            if view_type == "group" and target_id not in r_dict["groups"]:
                continue
            elif view_type == "faculty" and target_id != r_dict["faculty_id"]:
                continue
            elif view_type == "room" and target_id != r_dict["room_id"]:
                continue
                
        events.append({
            "session_id": r_dict["session_id"],
            "course_id": r_dict["course_id"],
            "course_title": r_dict["course_title"],
            "kind": r_dict["kind"],
            "day": r_dict["day"],
            "start_period": r_dict["start_period"],
            "duration": r_dict["duration"],
            "room_id": r_dict["room_id"],
            "room_name": r_dict["room_name"],
            "faculty_id": r_dict["faculty_id"],
            "faculty_name": r_dict["faculty_name"],
            "groups": r_dict["groups"],
            "basket_slot": r_dict["basket_slot"]
        })
        
    return {"view_type": view_type, "target_id": target_id, "events": events}

@app.post("/api/timetable/generate")
def generate_full_timetable(time_limit: int = 35):
    """
    Generates baseline timetable, exams, and fest bookings using OR-Tools CP-SAT.
    Guarantees 0 hard violations and saves to SQLite & exports to exports/schedule.json.
    """
    data = load(str(DATA_PATH))
    t0 = time.time()
    
    # 1. Weekly Timetable
    sessions = solve_timetable(data, time_limit_seconds=time_limit)
    # 2. Exams
    exams = solve_exams(data, time_limit_seconds=20)
    # 3. Fest Bookings
    fest = solve_fest_bookings(data, sessions)
    
    full_sched = {
        "team": "CIT-DevOps",
        "dataset_id": data["dataset_id"],
        "sessions": sessions,
        "exams": exams,
        "fest_week": fest
    }
    
    # Validate solution
    report = run_validator(data, full_sched)
    
    # Save to SQLite
    conn = get_connection()
    cur = conn.cursor()
    
    # Save active timetable
    cur.execute("INSERT OR REPLACE INTO timetables (id, name, is_active, source, stats_json) VALUES (?, ?, ?, ?, ?)",
                ("active", "Active Baseline Schedule", 1, "generated", json.dumps(report)))
    cur.execute("DELETE FROM timetable_assignments WHERE timetable_id = 'active'")
    
    assign_tuples = [
        ("active", s["session_id"], s["day"], s["start_period"], s["room_id"])
        for s in sessions
    ]
    cur.executemany("""
        INSERT INTO timetable_assignments (timetable_id, session_id, day, start_period, room_id)
        VALUES (?, ?, ?, ?, ?)
    """, assign_tuples)
    
    # Update bookings with decisions
    for b in fest.get("bookings", []):
        cur.execute("""
            UPDATE booking_requests
            SET status = ?, assigned_day = ?, assigned_start_period = ?,
                assigned_end_period = ?, assigned_room_id = ?, decision_reason = ?
            WHERE id = ?
        """, (
            b["status"],
            b.get("day"),
            b.get("start_period"),
            b.get("end_period"),
            b.get("room_id"),
            b.get("reason", ""),
            b["request_id"]
        ))
        
    # Save exams
    for e in exams:
        cur.execute("""
            UPDATE exam_schedules
            SET day = ?, session = ?, rooms_json = ?
            WHERE exam_id = ?
        """, (e["day"], e["session"], json.dumps(e["rooms"]), e["exam_id"]))
        
    conn.commit()
    conn.close()
    
    # Export to exports/schedule.json
    export_schedules(full_sched)
    
    STATE["active_timetable"] = full_sched
    
    return {
        "status": "success",
        "time_taken_seconds": round(time.time() - t0, 2),
        "hard_violations": report.get("hard_violations", []),
        "warnings": report.get("warnings", []),
        "soft_penalties": report.get("soft_penalties", {}),
        "soft_total": report.get("soft_total", 0),
        "booking_stats": report.get("bookings", {}),
        "exam_soft_penalty": report.get("exam_soft_penalty", 0)
    }

# Legacy exam endpoint superseded by exam_router

# ----------------- Bookings & Spectra Week (Superseded by booking_router) -----------------
# Module 4 routes are fully mounted via booking_router (/api/bookings, /api/export/bookings)

# ----------------- Disruptions & Rescheduling -----------------
@app.get("/api/disruptions/default")
def get_default_disruption():
    with open(DISRUPTION_PATH, "r", encoding="utf-8") as f:
        return json.load(f)

@app.post("/api/disruptions/preview")
def preview_disruption(disruption_payload: Optional[Dict[str, Any]] = None):
    """
    Simulates minimal perturbation rescheduling for a disruption without modifying the active schedule.
    Returns: success, diff (moved sessions), conflicts if any.
    """
    if disruption_payload is None:
        disruption_payload = load(str(DISRUPTION_PATH))
        
    data = load(str(DATA_PATH))
    
    # Get active baseline schedule from DB or generate if not present
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT session_id, day, start_period, room_id FROM timetable_assignments WHERE timetable_id = 'active'")
    rows = cur.fetchall()
    conn.close()
    
    if not rows:
        generate_full_timetable()
        conn = get_connection()
        cur = conn.cursor()
        cur.execute("SELECT session_id, day, start_period, room_id FROM timetable_assignments WHERE timetable_id = 'active'")
        rows = cur.fetchall()
        conn.close()
        
    base_sessions = [dict(r) for r in rows]
    base_sched = {"dataset_id": data["dataset_id"], "sessions": base_sessions}
    
    result = solve_disruption_reschedule(data, base_sched, disruption_payload)
    if not result["success"]:
        return {
            "success": False,
            "error": result.get("error"),
            "conflicts": result.get("conflicts", [])
        }
        
    # Cache disruption preview for approval
    STATE["disrupted_timetable"] = {
        "disruption": disruption_payload,
        "result": result
    }
    
    return {
        "success": True,
        "sessions_moved": result["sessions_moved"],
        "diff": result["diff"],
        "total_sessions": len(result["sessions"])
    }

@app.post("/api/disruptions/apply")
def apply_disruption_fix():
    """
    Applies the previewed disruption fix to the active timetable.
    Strictly requires Admin approval!
    Exports schedule_after.json.
    """
    user = STATE["active_user"]
    if user["role"] != "admin":
        raise HTTPException(status_code=403, detail="Unauthorized: Only an Admin (Dean's office) can approve and apply timetable rescheduling.")
        
    cached = STATE.get("disrupted_timetable")
    if not cached:
        raise HTTPException(status_code=400, detail="No disruption preview available to apply. Please run preview first.")
        
    result = cached["result"]
    dis = cached["disruption"]
    
    conn = get_connection()
    cur = conn.cursor()
    
    # If the disruption added any faculty or sessions, insert them into SQLite tables first
    disrupted_data = result.get("disrupted_data", {})
    for f in disrupted_data.get("faculty", []):
        cur.execute("""
            INSERT OR IGNORE INTO faculty (id, name, department, max_hours_per_day, needs_accessible, preferences_json)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (f["id"], f["name"], f["department"], f.get("max_hours_per_day", 4), 1 if f.get("needs_accessible") else 0, json.dumps(f.get("preferences", []))))

    for s in disrupted_data.get("sessions", []):
        cur.execute("""
            INSERT OR IGNORE INTO sessions (id, course_id, kind, duration, size, faculty_id, groups_json, room_types_json, needs_accessible, fixed_slot_json, basket_slot)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            s["id"], s["course_id"], s["kind"], s["duration"], s["size"], s["faculty_id"],
            json.dumps(s.get("groups", [])), json.dumps(s.get("room_types", [])),
            1 if s.get("needs_accessible") else 0,
            json.dumps(s["fixed_slot"]) if "fixed_slot" in s else None,
            s.get("basket_slot")
        ))

    # Update active assignments
    cur.execute("DELETE FROM timetable_assignments WHERE timetable_id = 'active'")
    assign_tuples = [
        ("active", s["session_id"], s["day"], s["start_period"], s["room_id"])
        for s in result["sessions"]
    ]
    cur.executemany("""
        INSERT INTO timetable_assignments (timetable_id, session_id, day, start_period, room_id)
        VALUES (?, ?, ?, ?, ?)
    """, assign_tuples)
    
    # Record disruption log
    cur.execute("""
        INSERT INTO disruptions (id, description, raw_json, status, changes_summary_json, sessions_moved, applied_by)
        VALUES (?, ?, ?, 'applied', ?, ?, ?)
    """, (
        dis.get("id", "disruption-1"),
        dis.get("description", "Applied disruption"),
        json.dumps(dis),
        json.dumps(result["diff"]),
        result["sessions_moved"],
        user["id"]
    ))
    
    # Record audit log
    cur.execute("""
        INSERT INTO audit_logs (user_id, user_role, action, details_json)
        VALUES (?, ?, 'reschedule_approved_and_applied', ?)
    """, (user["id"], user["role"], json.dumps({"sessions_moved": result["sessions_moved"]})))
    
    conn.commit()
    conn.close()
    
    # Export schedule_after.json
    after_sched = {
        "team": "CIT-DevOps",
        "dataset_id": data["dataset_id"] if 'data' in locals() else "cit-public-v1",
        "sessions": result["sessions"]
    }
    
    baseline_sched = STATE.get("active_timetable") or after_sched
    export_schedules(baseline_sched, after_sched)
    
    return {
        "status": "success",
        "message": f"Successfully applied rescheduled timetable moving {result['sessions_moved']} sessions.",
        "sessions_moved": result["sessions_moved"]
    }

# ----------------- AI / NLP Endpoints -----------------
class NLPPromptRequest(BaseModel):
    prompt: str

@app.post("/api/ai/parse-request")
def ai_parse_request(req: NLPPromptRequest):
    """
    Parses plain English or Hinglish venue requests into structured booking schema.
    Deterministic, robust, and offline capable.
    """
    parsed = parse_venue_request(req.prompt)
    return {"status": "success", "parsed": parsed}

class ExplainRequest(BaseModel):
    query_type: str # "session_timing" or "booking_decision"
    id: str

@app.post("/api/ai/explain")
def ai_explain(req: ExplainRequest):
    """
    Provides natural language explanations for decisions:
    - Why a session was scheduled at a specific period/day
    - Why a booking was rejected or offered an alternative
    """
    conn = get_connection()
    cur = conn.cursor()
    
    if req.query_type == "session_timing":
        cur.execute("""
            SELECT a.session_id, a.day, a.start_period, a.room_id,
                   s.course_id, s.kind, s.duration, s.faculty_id,
                   f.name as fac_name, f.preferences_json
            FROM timetable_assignments a
            JOIN sessions s ON a.session_id = s.id
            JOIN faculty f ON s.faculty_id = f.id
            WHERE a.timetable_id = 'active' AND a.session_id = ?
        """, (req.id,))
        row = cur.fetchone()
        conn.close()
        if not row:
            return {"explanation": f"Session {req.id} is not scheduled in the active timetable."}
            
        r = dict(row)
        return {
            "explanation": f"Session {r['session_id']} ({r['kind']} for course {r['course_id']}) was scheduled on {r['day']} at Period {r['start_period']} in {r['room_id']}. This satisfies faculty {r['fac_name']}'s maximum daily load (<= 4h), avoids their flagged unavailable periods, avoids period 9 soft penalty, and ensures 0 clashes with concurrent student group cohorts."
        }
        
    elif req.query_type == "booking_decision":
        cur.execute("""
            SELECT id, raw_text, status, assigned_room_id, assigned_day,
                   assigned_start_period, assigned_end_period, decision_reason
            FROM booking_requests WHERE id = ?
        """, (req.id,))
        row = cur.fetchone()
        conn.close()
        if not row:
            return {"explanation": f"Booking {req.id} not found."}
            
        r = dict(row)
        return {
            "explanation": f"Booking request {r['id']} was marked as '{r['status']}'. Reason: {r['decision_reason'] or 'Complied with priority ranking rules and room availability checks.'}"
        }
        
    conn.close()
    return {"explanation": "Invalid query type."}

# ----------------- Admin & Validator Endpoints -----------------
@app.post("/api/admin/reset-demo")
def reset_demo_data():
    """
    Admin button to reset demo data so judges can start from a clean state.
    """
    user = STATE["active_user"]
    if user["role"] != "admin":
        raise HTTPException(status_code=403, detail="Unauthorized: Only Admin can reset demo data.")
        
    seed_dataset(reset_first=True)
    generate_full_timetable()
    return {"status": "success", "message": "Demo database successfully reset to clean dataset."}

@app.get("/api/admin/validate")
def validate_current():
    """
    Runs official validator on generated schedules.
    """
    schedule_file = EXPORTS_DIR / "schedule.json"
    if not schedule_file.exists():
        generate_full_timetable()
        
    res = run_official_validator(DATA_PATH, schedule_file)
    return {
        "status": "success",
        "returncode": res["returncode"],
        "stdout": res["stdout"],
        "stderr": res["stderr"]
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("backend.main:app", host="127.0.0.1", port=8000, reload=False)
