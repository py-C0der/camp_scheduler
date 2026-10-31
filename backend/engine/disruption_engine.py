import json
import time
from pathlib import Path
from collections import defaultdict
from ortools.sat.python import cp_model
from CrunchWeek_StarterPack.validator import apply_disruption, to_assign, check_timetable, Ctx

def solve_disruption_reschedule(data, baseline_schedule, disruption_data, time_limit_seconds=45):
    """
    Applies disruption to the dataset and solves for a minimal perturbation timetable.
    Objective: Minimize the number of sessions moved from baseline_schedule.
    """
    # 1. Apply disruption changes to data
    disrupted_data = apply_disruption(data, disruption_data)
    
    # Baseline assignment map: sid -> (day, start_p, room_id)
    base_assign, _ = to_assign(baseline_schedule)
    
    days = disrupted_data["calendar"]["days"]
    day_to_idx = {d: i for i, d in enumerate(days)}
    idx_to_day = {i: d for i, d in enumerate(days)}
    num_days = len(days)
    
    teaching_periods = list(range(1, 10))
    lunch_after = disrupted_data["calendar"]["lunch"]["after_period"]
    lab_starts = set(disrupted_data["calendar"]["lab_start_periods"])
    
    rooms = {r["id"]: r for r in disrupted_data["rooms"]}
    faculty = {f["id"]: f for f in disrupted_data["faculty"]}
    groups = {g["id"]: g for g in disrupted_data["student_groups"]}
    sessions = {s["id"]: s for s in disrupted_data["sessions"]}
    
    # Precompute unavailabilities
    fac_unavail = set()
    for f in disrupted_data["faculty"]:
        for u in f.get("unavailable", []):
            d_idx = day_to_idx[u["day"]]
            for p in u["periods"]:
                fac_unavail.add((f["id"], d_idx, p))
                
    room_unavail = set()
    for u in disrupted_data.get("room_unavailability", []):
        d_idx = day_to_idx[u["day"]]
        for p in u["periods"]:
            room_unavail.add((u["room_id"], d_idx, p))
            
    # Session candidate slots
    session_candidates = {}
    for sid, s in sessions.items():
        dur = s["duration"]
        cand = []
        valid_rooms = []
        for rid, r in rooms.items():
            allowed = r.get("allowed_uses", [])
            if s["kind"] == "lab":
                if "lab" not in allowed: continue
            elif s["kind"] in ("lecture", "tutorial"):
                if "lecture" not in allowed and "tutorial" not in allowed: continue
            if r["type"] not in s["room_types"] or r["capacity"] < s["size"]:
                continue
            if s.get("needs_accessible") and not r.get("accessible"):
                continue
            valid_rooms.append(rid)
            
        fixed = s.get("fixed_slot")
        for d_idx, d_name in enumerate(days):
            if fixed and fixed["day"] != d_name:
                continue
            for start_p in teaching_periods:
                end_p = start_p + dur - 1
                if end_p > 9:
                    continue
                if start_p <= lunch_after and end_p > lunch_after:
                    continue
                if s["kind"] == "lab" and start_p not in lab_starts:
                    continue
                if fixed and fixed["start_period"] != start_p:
                    continue
                f_id = s["faculty_id"]
                if any((f_id, d_idx, p) in fac_unavail for p in range(start_p, end_p + 1)):
                    continue
                for rid in valid_rooms:
                    if any((rid, d_idx, p) in room_unavail for p in range(start_p, end_p + 1)):
                        continue
                    cand.append((d_idx, start_p, rid))
                    
        if not cand:
            return {
                "success": False,
                "error": f"Conflict: No valid slot/room exists for session {sid} under new constraints.",
                "conflicts": [f"Session {sid} cannot be scheduled due to faculty or room unavailability."]
            }
        session_candidates[sid] = cand

    model = cp_model.CpModel()
    x = {}
    session_vars = defaultdict(list)
    moved_vars = []
    
    basket_sessions = defaultdict(list)
    for sid, s in sessions.items():
        if s.get("basket_slot"):
            basket_sessions[s["basket_slot"]].append(sid)

    for sid, cand in session_candidates.items():
        base_slot = base_assign.get(sid)
        for (d_idx, start_p, rid) in cand:
            var = model.NewBoolVar(f"x_dis_{sid}_{d_idx}_{start_p}_{rid}")
            x[sid, d_idx, start_p, rid] = var
            session_vars[sid].append(var)
            
            # If this candidate is DIFFERENT from baseline slot, it counts as moved!
            is_same = False
            if base_slot:
                b_day, b_start, b_rid = base_slot
                if idx_to_day[d_idx] == b_day and start_p == b_start and rid == b_rid:
                    is_same = True
            if not is_same:
                # Adding to moved penalty
                moved_vars.append(var)
                
        model.AddExactlyOne(session_vars[sid])
        
    # Basket constraints
    for b_slot, sids in basket_sessions.items():
        ref_sid = sids[0]
        for other_sid in sids[1:]:
            for d_idx in range(num_days):
                for p in teaching_periods:
                    vars_ref = [x[ref_sid, d, sp, r] for (d, sp, r) in session_candidates[ref_sid] if d == d_idx and sp == p]
                    vars_oth = [x[other_sid, d, sp, r] for (d, sp, r) in session_candidates[other_sid] if d == d_idx and sp == p]
                    if vars_ref or vars_oth:
                        model.Add(sum(vars_ref) == sum(vars_oth))

    # Room, Faculty, Group non-overlap
    room_time_map = defaultdict(list)
    fac_time_map = defaultdict(list)
    grp_time_map = defaultdict(lambda: defaultdict(list))
    
    for sid, cand in session_candidates.items():
        s = sessions[sid]
        f_id = s["faculty_id"]
        dur = s["duration"]
        b_key = s.get("basket_slot") or sid
        for (d_idx, start_p, rid) in cand:
            var = x[sid, d_idx, start_p, rid]
            for p in range(start_p, start_p + dur):
                room_time_map[(rid, d_idx, p)].append(var)
                fac_time_map[(f_id, d_idx, p)].append(var)
                for g in s["groups"]:
                    grp_time_map[(g, d_idx, p)][b_key].append(var)
                    
    for (rid, d_idx, p), var_list in room_time_map.items():
        if len(var_list) > 1:
            model.Add(sum(var_list) <= 1)
            
    for (f_id, d_idx, p), var_list in fac_time_map.items():
        if len(var_list) > 1:
            model.Add(sum(var_list) <= 1)
            
    for (g, d_idx, p), basket_dict in grp_time_map.items():
        if len(basket_dict) > 1:
            active_keys = []
            for b_key, var_list in basket_dict.items():
                b_act = model.NewBoolVar(f"grp_act_dis_{g}_{d_idx}_{p}_{b_key}")
                model.Add(sum(var_list) >= b_act)
                model.Add(sum(var_list) <= len(var_list) * b_act)
                active_keys.append(b_act)
            model.Add(sum(active_keys) <= 1)

    # Faculty max daily hours
    for f_id, f in faculty.items():
        max_h = f.get("max_hours_per_day", 4)
        for d_idx in range(num_days):
            day_hours = []
            for sid, s in sessions.items():
                if s["faculty_id"] == f_id:
                    dur = s["duration"]
                    for (d, sp, rid) in session_candidates[sid]:
                        if d == d_idx:
                            day_hours.append(dur * x[sid, d, sp, rid])
            if day_hours:
                model.Add(sum(day_hours) <= max_h)

    # Primary Objective: Minimize number of sessions moved!
    # Secondary: Soft preferences
    model.Minimize(sum(moved_vars))
    
    solver = cp_model.CpSolver()
    solver.parameters.max_time_in_seconds = time_limit_seconds
    solver.parameters.num_workers = 8
    
    print(f"Solving minimal perturbation rescheduling model (timeout: {time_limit_seconds}s)...")
    status = solver.Solve(model)
    
    if status not in (cp_model.OPTIMAL, cp_model.FEASIBLE):
        return {
            "success": False,
            "error": "Infeasible: No valid timetable can be found that satisfies all hard constraints.",
            "conflicts": ["Constraints conflict across room and faculty unavailability."]
        }

    # Extract new timetable
    new_assignments = []
    diff = []
    sessions_moved_count = 0
    
    for sid, cand in session_candidates.items():
        for (d_idx, start_p, rid) in cand:
            if solver.Value(x[sid, d_idx, start_p, rid]) == 1:
                d_name = idx_to_day[d_idx]
                new_assignments.append({
                    "session_id": sid,
                    "day": d_name,
                    "start_period": start_p,
                    "room_id": rid
                })
                base_slot = base_assign.get(sid)
                if base_slot:
                    b_day, b_start, b_rid = base_slot
                    if (d_name != b_day) or (start_p != b_start) or (rid != b_rid):
                        sessions_moved_count += 1
                        diff.append({
                            "session_id": sid,
                            "course_id": sessions[sid]["course_id"],
                            "faculty_id": sessions[sid]["faculty_id"],
                            "groups": sessions[sid]["groups"],
                            "from": {"day": b_day, "start_period": b_start, "room_id": b_rid},
                            "to": {"day": d_name, "start_period": start_p, "room_id": rid}
                        })
                else:
                    # Brand new added session
                    diff.append({
                        "session_id": sid,
                        "course_id": sessions[sid]["course_id"],
                        "faculty_id": sessions[sid]["faculty_id"],
                        "groups": sessions[sid]["groups"],
                        "from": None,
                        "to": {"day": d_name, "start_period": start_p, "room_id": rid},
                        "action": "added"
                    })
                break
                
    return {
        "success": True,
        "disrupted_data": disrupted_data,
        "sessions": new_assignments,
        "sessions_moved": sessions_moved_count,
        "diff": diff
    }

if __name__ == "__main__":
    from CrunchWeek_StarterPack.validator import load
    data = load("CrunchWeek_StarterPack/data/cit_public.json")
    from backend.engine.timetable_solver import solve_timetable
    base = solve_timetable(data, time_limit_seconds=30)
    baseline_sched = {"dataset_id": data["dataset_id"], "sessions": base}
    
    dis = load("CrunchWeek_StarterPack/examples/sample_disruption.json")
    res = solve_disruption_reschedule(data, baseline_sched, dis)
    print(f"Reschedule success: {res['success']}, Sessions moved: {res.get('sessions_moved')}")
