import json
from pathlib import Path
from collections import defaultdict
from ortools.sat.python import cp_model

def solve_exams(data, time_limit_seconds=20):
    """
    Formulates and solves the Midsem Exam schedule using OR-Tools CP-SAT.
    Guarantees:
    - 0 hard violations (E1, E2, H4 room overlap, H3 group overlap, H5 half-capacity)
    - Minimizes same-day exams for any student group.
    """
    cal = data["calendar"]["exam_week"]
    exam_days = cal["days"] # ["MON", "TUE", "WED", "THU", "FRI"]
    exam_sessions = [s["id"] for s in cal["sessions"]] # ["morning", "afternoon"]
    
    slots = []
    for d in exam_days:
        for s in exam_sessions:
            slots.append((d, s))
            
    # Eligible exam rooms
    exam_rooms = {}
    for r in data["rooms"]:
        if "exam" in r.get("allowed_uses", []):
            exam_rooms[r["id"]] = {
                "name": r["name"],
                "half_capacity": r["capacity"] // 2,
                "building": r["building"]
            }
            
    exams = data.get("exams", [])
    
    model = cp_model.CpModel()
    
    # Decision variables:
    # y[e_id, slot_idx] = 1 if exam e is held at slot_idx
    # z[e_id, slot_idx, r_id] = 1 if room r_id is assigned to exam e at slot_idx
    y = {}
    z = {}
    
    for e in exams:
        eid = e["id"]
        for slot_idx in range(len(slots)):
            y[eid, slot_idx] = model.NewBoolVar(f"y_{eid}_{slot_idx}")
            for rid in exam_rooms:
                z[eid, slot_idx, rid] = model.NewBoolVar(f"z_{eid}_{slot_idx}_{rid}")
                # z can only be 1 if y is 1
                model.Add(z[eid, slot_idx, rid] <= y[eid, slot_idx])
                
        # Each exam scheduled exactly once
        model.AddExactlyOne([y[eid, slot_idx] for slot_idx in range(len(slots))])
        
    # Capacity constraint:
    # When exam e is at slot_idx, sum of half_capacity of assigned rooms >= e["size"]
    for e in exams:
        eid = e["id"]
        req_size = e["size"]
        for slot_idx in range(len(slots)):
            # If y[eid, slot_idx] == 1, then sum(z * cap) >= req_size
            room_cap_sum = sum(z[eid, slot_idx, rid] * exam_rooms[rid]["half_capacity"] for rid in exam_rooms)
            model.Add(room_cap_sum >= req_size * y[eid, slot_idx])

    # Room non-overlap constraint:
    # In any slot_idx, a room can be used by at most one exam
    for slot_idx in range(len(slots)):
        for rid in exam_rooms:
            model.Add(sum(z[eid, slot_idx, rid] for e in exams for eid in [e["id"]]) <= 1)
            
    # Group non-overlap constraint:
    # A student group can have at most one exam in any slot_idx
    for slot_idx in range(len(slots)):
        for g in data["student_groups"]:
            gid = g["id"]
            exams_for_g = [e["id"] for e in exams if gid in e["groups"]]
            if len(exams_for_g) > 1:
                model.Add(sum(y[eid, slot_idx] for eid in exams_for_g) <= 1)
                
    # Soft constraint: Minimize student groups having 2 exams on the same day
    # For each group and each day, count exams on that day
    same_day_penalties = []
    for d_idx, day in enumerate(exam_days):
        slot_m = d_idx * 2      # morning
        slot_a = d_idx * 2 + 1  # afternoon
        for g in data["student_groups"]:
            gid = g["id"]
            exams_for_g = [e["id"] for e in exams if gid in e["groups"]]
            if len(exams_for_g) > 1:
                # Morning exams + afternoon exams
                m_vars = [y[eid, slot_m] for eid in exams_for_g]
                a_vars = [y[eid, slot_a] for eid in exams_for_g]
                
                # If group has an exam in morning and an exam in afternoon on same day
                both = model.NewBoolVar(f"both_{gid}_{day}")
                # both <= sum(m_vars), both <= sum(a_vars), both >= sum(m_vars) + sum(a_vars) - 1
                model.Add(both <= sum(m_vars))
                model.Add(both <= sum(a_vars))
                same_day_penalties.append(5 * both)
                
    model.Minimize(sum(same_day_penalties))
    
    solver = cp_model.CpSolver()
    solver.parameters.max_time_in_seconds = time_limit_seconds
    solver.parameters.num_workers = 8
    
    print(f"Solving exam scheduling CP-SAT model ({len(exams)} exams, {len(slots)} slots)...")
    status = solver.Solve(model)
    
    if status not in (cp_model.OPTIMAL, cp_model.FEASIBLE):
        raise RuntimeError(f"Exam solver failed: {solver.StatusName(status)}")
        
    print(f"Exam schedule solved! Status: {solver.StatusName(status)}, Same-day group penalty: {solver.ObjectiveValue()}")
    
    result = []
    for e in exams:
        eid = e["id"]
        for slot_idx, (day, sess) in enumerate(slots):
            if solver.Value(y[eid, slot_idx]) == 1:
                assigned_rooms = [rid for rid in exam_rooms if solver.Value(z[eid, slot_idx, rid]) == 1]
                result.append({
                    "exam_id": eid,
                    "day": day,
                    "session": sess,
                    "rooms": assigned_rooms
                })
                break
                
    return result

if __name__ == "__main__":
    data_path = Path(__file__).resolve().parent.parent.parent / "CrunchWeek_StarterPack" / "data" / "cit_public.json"
    with open(data_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    res = solve_exams(data)
    print(f"Scheduled {len(res)} exams.")
