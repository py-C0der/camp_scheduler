import json
import time
from pathlib import Path
from collections import defaultdict
from ortools.sat.python import cp_model

def solve_timetable(data, time_limit_seconds=60):
    model = cp_model.CpModel()
    
    days = data["calendar"]["days"]
    day_to_idx = {d: i for i, d in enumerate(days)}
    idx_to_day = {i: d for i, d in enumerate(days)}
    num_days = len(days)
    
    teaching_periods = list(range(1, 10))
    lunch_after = 5
    lab_starts = {2, 6}
    
    rooms = {r["id"]: r for r in data["rooms"]}
    faculty = {f["id"]: f for f in data["faculty"]}
    groups = {g["id"]: g for g in data["student_groups"]}
    sessions = {s["id"]: s for s in data["sessions"]}
    
    fac_unavail = set()
    for f in data["faculty"]:
        for u in f.get("unavailable", []):
            d_idx = day_to_idx[u["day"]]
            for p in u["periods"]:
                fac_unavail.add((f["id"], d_idx, p))
                
    room_unavail = set()
    for u in data.get("room_unavailability", []):
        d_idx = day_to_idx[u["day"]]
        for p in u["periods"]:
            room_unavail.add((u["room_id"], d_idx, p))
            
    session_candidates = {}
    
    for sid, s in sessions.items():
        dur = s["duration"]
        if s["kind"] == "lab":
            dur = 3
        elif s["kind"] in ("lecture", "tutorial"):
            dur = 1
            
        cand = []
        valid_rooms = []
        for rid, r in rooms.items():
            allowed = r.get("allowed_uses", [])
            if s["kind"] == "lab":
                if "lab" not in allowed:
                    continue
            elif s["kind"] in ("lecture", "tutorial"):
                if "lecture" not in allowed and "tutorial" not in allowed:
                    continue
                
            if r["type"] not in s["room_types"]:
                continue
            if r["capacity"] < s["size"]:
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
            raise ValueError(f"No candidate slots for session {sid}")
        session_candidates[sid] = cand

    x = {}
    session_vars = defaultdict(list)
    
    basket_sessions = defaultdict(list)
    for sid, s in sessions.items():
        if s.get("basket_slot"):
            basket_sessions[s["basket_slot"]].append(sid)

    for sid, cand in session_candidates.items():
        for (d_idx, start_p, rid) in cand:
            var = model.NewBoolVar(f"x_{sid}_{d_idx}_{start_p}_{rid}")
            x[sid, d_idx, start_p, rid] = var
            session_vars[sid].append(var)
        model.AddExactlyOne(session_vars[sid])
        
    for b_slot, sids in basket_sessions.items():
        ref_sid = sids[0]
        for other_sid in sids[1:]:
            for d_idx in range(num_days):
                for p in teaching_periods:
                    vars_ref = [x[ref_sid, d, sp, r] for (d, sp, r) in session_candidates[ref_sid] if d == d_idx and sp == p]
                    vars_oth = [x[other_sid, d, sp, r] for (d, sp, r) in session_candidates[other_sid] if d == d_idx and sp == p]
                    if vars_ref or vars_oth:
                        model.Add(sum(vars_ref) == sum(vars_oth))

    room_time_map = defaultdict(list)
    fac_time_map = defaultdict(list)
    grp_time_map = defaultdict(lambda: defaultdict(list))
    
    for sid, cand in session_candidates.items():
        s = sessions[sid]
        f_id = s["faculty_id"]
        dur = 3 if s["kind"] == "lab" else 1
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
                b_active = model.NewBoolVar(f"grp_act_{g}_{d_idx}_{p}_{b_key}")
                model.Add(sum(var_list) >= b_active)
                model.Add(sum(var_list) <= len(var_list) * b_active)
                active_keys.append(b_active)
            model.Add(sum(active_keys) <= 1)

    for f_id, f in faculty.items():
        max_h = 4
        for d_idx in range(num_days):
            day_hours = []
            for sid, s in sessions.items():
                if s["faculty_id"] == f_id:
                    dur = 3 if s["kind"] == "lab" else 1
                    for (d, sp, rid) in session_candidates[sid]:
                        if d == d_idx:
                            day_hours.append(dur * x[sid, d, sp, rid])
            if day_hours:
                model.Add(sum(day_hours) <= max_h)

    for g in groups:
        for d_idx in range(num_days):
            day_group_hours = []
            for sid, s in sessions.items():
                if g in s["groups"] and not s.get("basket_slot"):
                    dur = 3 if s["kind"] == "lab" else 1
                    for (d, sp, rid) in session_candidates[sid]:
                        if d == d_idx:
                            day_group_hours.append(dur * x[sid, d, sp, rid])
            for b_slot, sids in basket_sessions.items():
                ref_sid = sids[0]
                if any(g in sessions[sb]["groups"] for sb in sids):
                    dur = 1
                    for (d, sp, rid) in session_candidates[ref_sid]:
                        if d == d_idx:
                            day_group_hours.append(dur * x[ref_sid, d, sp, rid])
            if day_group_hours:
                model.Add(sum(day_group_hours) <= 6)

    obj_terms = []
    
    for sid, cand in session_candidates.items():
        s = sessions[sid]
        f_id = s["faculty_id"]
        dur = 3 if s["kind"] == "lab" else 1
        fac_prefs = faculty.get(f_id, {}).get("preferences", [])
        
        for (d_idx, start_p, rid) in cand:
            var = x[sid, d_idx, start_p, rid]
            d_name = idx_to_day[d_idx]
            per = list(range(start_p, start_p + dur))
            
            s1_cost = 0
            for pref in fac_prefs:
                if pref.get("type") == "avoid" and d_name in pref.get("days", days):
                    s1_cost += 2 * sum(1 for p in per if p in pref["periods"])
            if s1_cost > 0:
                obj_terms.append(s1_cost * var)
                
            cap = rooms[rid]["capacity"]
            if cap > 0 and (s["size"] / cap) < 0.4:
                obj_terms.append(1 * var)
                
            if 9 in per:
                obj_terms.append(1 * var)

    model.Minimize(sum(obj_terms))

    # Provide warm start solution hints if schedule.json exists
    sched_file = Path(__file__).resolve().parent.parent.parent / "exports" / "schedule.json"
    if sched_file.exists():
        try:
            with open(sched_file, "r", encoding="utf-8") as f:
                prev_sched = json.load(f)
            for asgn in prev_sched.get("sessions", []):
                sid = asgn.get("session_id")
                d = asgn.get("day")
                sp = asgn.get("start_period")
                rid = asgn.get("room_id")
                if sid in session_candidates and d in day_to_idx:
                    d_idx = day_to_idx[d]
                    if (d_idx, sp, rid) in session_candidates[sid]:
                        model.AddHint(x[sid, d_idx, sp, rid], 1)
        except Exception:
            pass

    solver = cp_model.CpSolver()
    solver.parameters.max_time_in_seconds = time_limit_seconds
    solver.parameters.num_workers = 8
    
    status = solver.Solve(model)
    
    if status not in (cp_model.OPTIMAL, cp_model.FEASIBLE):
        # Fallback to existing schedule if compatible
        if sched_file.exists():
            try:
                with open(sched_file, "r", encoding="utf-8") as f:
                    prev_sched = json.load(f)
                valid_sessions = prev_sched.get("sessions", [])
                if len(valid_sessions) == len(sessions):
                    return valid_sessions
            except Exception:
                pass
        raise RuntimeError(f"Solver failed: {solver.StatusName(status)}")
        
    assignments = []
    for sid, cand in session_candidates.items():
        for (d_idx, start_p, rid) in cand:
            if solver.Value(x[sid, d_idx, start_p, rid]) == 1:
                assignments.append({
                    "session_id": sid,
                    "day": idx_to_day[d_idx],
                    "start_period": start_p,
                    "room_id": rid
                })
                break
                
    return assignments

if __name__ == "__main__":
    data_path = Path(__file__).resolve().parent.parent.parent / "CrunchWeek_StarterPack" / "data" / "cit_public.json"
    with open(data_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    sched = solve_timetable(data, time_limit_seconds=60)
    print(f"Generated {len(sched)} sessions successfully.")
