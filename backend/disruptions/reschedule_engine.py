"""
Intelligent Timetable Rescheduling Engine.
Reuses and extends Google OR-Tools CP-SAT optimization model to compute minimal-perturbation
timetables that satisfy all hard constraints while preserving unaffected sessions.
Independently verifies results with the official tournament validator.
"""

import time
import copy
import json
from pathlib import Path
from collections import defaultdict
from typing import Dict, Any, List, Optional, Tuple
from ortools.sat.python import cp_model

from CrunchWeek_StarterPack.validator import apply_disruption, to_assign, check_timetable, run as run_official_validator, Ctx


class TimetableReschedulingEngine:
    """Computes constraint-safe minimal disruption rescheduling proposals."""

    @staticmethod
    def reschedule(
        dataset: Dict[str, Any],
        baseline_schedule: Dict[str, Any],
        disruption_payload: Dict[str, Any],
        time_limit_seconds: int = 45
    ) -> Dict[str, Any]:
        """
        Executes CP-SAT minimal perturbation rescheduling:
        1. Applies disruption changes (faculty downtime, room downtime, session additions/removals).
        2. Preserves baseline assignments by adding penalty for every moved session.
        3. Formulates non-overlap and load constraints.
        4. Validates proposed schedule independently using official validator.
        """
        start_time = time.time()

        # Apply disruption changes
        disrupted_data = apply_disruption(dataset, disruption_payload)
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

        # Precompute faculty downtime
        fac_unavail = set()
        for f in disrupted_data["faculty"]:
            for u in f.get("unavailable", []):
                if u["day"] in day_to_idx:
                    d_idx = day_to_idx[u["day"]]
                    for p in u["periods"]:
                        fac_unavail.add((f["id"], d_idx, p))

        # Precompute room downtime
        room_unavail = set()
        for u in disrupted_data.get("room_unavailability", []):
            if u["day"] in day_to_idx:
                d_idx = day_to_idx[u["day"]]
                for p in u["periods"]:
                    room_unavail.add((u["room_id"], d_idx, p))

        # Check fest_week bookings to avoid cross-module festival collisions (H13)
        fest_bookings = baseline_schedule.get("fest_week", {}).get("bookings", [])
        if not fest_bookings:
            export_path = Path("exports/schedule.json")
            if export_path.exists():
                try:
                    with open(export_path, "r", encoding="utf-8") as f:
                        base_exp = json.load(f)
                        fest_bookings = base_exp.get("fest_week", {}).get("bookings", [])
                except Exception:
                    pass

        fest_busy_slots = set()
        for b in fest_bookings:
            if b.get("status") == "approved" and b.get("room_id") and b.get("day") in day_to_idx:
                d_idx = day_to_idx[b["day"]]
                for p in range(b.get("start_period", 1), b.get("end_period", 1) + 1):
                    fest_busy_slots.add((b["room_id"], d_idx, p))

        # Generate candidate slots per session
        session_candidates = {}
        for sid, s in sessions.items():
            dur = s["duration"]
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
                if r["type"] not in s["room_types"] or r["capacity"] < s["size"]:
                    continue
                if s.get("needs_accessible") and not r.get("accessible"):
                    continue
                valid_rooms.append(rid)

            fixed = s.get("fixed_slot")
            for d_idx, d_name in enumerate(days):
                if fixed and fixed.get("day") != d_name:
                    continue
                for start_p in teaching_periods:
                    end_p = start_p + dur - 1
                    if end_p > 9:
                        continue
                    if start_p <= lunch_after and end_p > lunch_after:
                        continue
                    if s["kind"] == "lab" and start_p not in lab_starts:
                        continue
                    if fixed and fixed.get("start_period") != start_p:
                        continue
                    f_id = s["faculty_id"]
                    if any((f_id, d_idx, p) in fac_unavail for p in range(start_p, end_p + 1)):
                        continue
                    for rid in valid_rooms:
                        if any((rid, d_idx, p) in room_unavail for p in range(start_p, end_p + 1)):
                            continue
                        if any((rid, d_idx, p) in fest_busy_slots for p in range(start_p, end_p + 1)):
                            continue
                        cand.append((d_idx, start_p, rid))

            if not cand:
                return {
                    "success": False,
                    "solver_status": "INFEASIBLE",
                    "solve_time_seconds": round(time.time() - start_time, 2),
                    "error": f"No feasible slot exists for session {sid} under disruption constraints.",
                    "hard_violations_count": 1,
                    "hard_violations": [{"rule": "H_INFEASIBLE", "detail": f"Session {sid} cannot be placed"}],
                    "sessions_moved": 0,
                    "proposed_sessions": []
                }
            session_candidates[sid] = cand

        # Build CP-SAT Model
        model = cp_model.CpModel()
        x = {}
        session_vars = defaultdict(list)
        moved_vars = []
        time_changed_vars = []
        room_changed_vars = []

        basket_sessions = defaultdict(list)
        for sid, s in sessions.items():
            if s.get("basket_slot"):
                basket_sessions[s["basket_slot"]].append(sid)

        for sid, cand in session_candidates.items():
            base_slot = base_assign.get(sid)
            for (d_idx, start_p, rid) in cand:
                var = model.NewBoolVar(f"x_{sid}_{d_idx}_{start_p}_{rid}")
                x[sid, d_idx, start_p, rid] = var
                session_vars[sid].append(var)

                # Track deviation from baseline
                if base_slot:
                    b_day, b_start, b_rid = base_slot
                    is_same_time = (idx_to_day[d_idx] == b_day and start_p == b_start)
                    is_same_room = (rid == b_rid)
                    if not (is_same_time and is_same_room):
                        moved_vars.append(var)
                    if not is_same_time:
                        time_changed_vars.append(var)
                    if is_same_time and not is_same_room:
                        room_changed_vars.append(var)

            model.AddExactlyOne(session_vars[sid])

        # Basket synchronization: Elective basket sessions must take the exact same time slot
        for b_slot, sids in basket_sessions.items():
            ref_sid = sids[0]
            for other_sid in sids[1:]:
                for d_idx in range(num_days):
                    for p in teaching_periods:
                        vars_ref = [x[ref_sid, d, sp, r] for (d, sp, r) in session_candidates[ref_sid] if d == d_idx and sp == p]
                        vars_oth = [x[other_sid, d, sp, r] for (d, sp, r) in session_candidates[other_sid] if d == d_idx and sp == p]
                        if vars_ref or vars_oth:
                            model.Add(sum(vars_ref) == sum(vars_oth))

        # Room, Faculty, Group non-overlap constraints
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
                    b_act = model.NewBoolVar(f"grp_act_{g}_{d_idx}_{p}_{b_key}")
                    model.Add(sum(var_list) >= b_act)
                    model.Add(sum(var_list) <= len(var_list) * b_act)
                    active_keys.append(b_act)
                model.Add(sum(active_keys) <= 1)

        # Faculty daily workload limit
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

        # Objective: Minimizing moved sessions as primary priority (weight 100), room changes (weight 1)
        model.Minimize(100 * sum(time_changed_vars) + sum(room_changed_vars))

        solver = cp_model.CpSolver()
        solver.parameters.max_time_in_seconds = time_limit_seconds
        solver.parameters.num_workers = 8

        status = solver.Solve(model)
        solve_duration = round(time.time() - start_time, 2)

        if status not in (cp_model.OPTIMAL, cp_model.FEASIBLE):
            return {
                "success": False,
                "solver_status": "INFEASIBLE" if status == cp_model.INFEASIBLE else "UNKNOWN",
                "solve_time_seconds": solve_duration,
                "error": "No valid rescheduling solution could be found satisfying all hard constraints.",
                "hard_violations_count": 1,
                "hard_violations": [{"rule": "H_INFEASIBLE", "detail": "Solver returned INFEASIBLE"}],
                "sessions_moved": 0,
                "proposed_sessions": []
            }

        # Extract proposed assignments and diff
        proposed_sessions = []
        assignment_items = []
        moved_count = 0
        time_changed_count = 0
        room_only_count = 0
        unchanged_count = 0

        for sid, cand in session_candidates.items():
            for (d_idx, start_p, rid) in cand:
                if solver.Value(x[sid, d_idx, start_p, rid]) == 1:
                    d_name = idx_to_day[d_idx]
                    proposed_sessions.append({
                        "session_id": sid,
                        "day": d_name,
                        "start_period": start_p,
                        "room_id": rid
                    })

                    meta = sessions[sid]
                    base_slot = base_assign.get(sid)

                    if base_slot:
                        b_day, b_start, b_rid = base_slot
                        is_same_time = (d_name == b_day and start_p == b_start)
                        is_same_room = (rid == b_rid)

                        if is_same_time and is_same_room:
                            change_type = "unchanged"
                            change_reason = "Preserved original assignment"
                            unchanged_count += 1
                            is_moved = False
                        elif not is_same_time and not is_same_room:
                            change_type = "time_and_room"
                            change_reason = f"Rescheduled from {b_day} P{b_start} in {b_rid} to avoid disruption"
                            moved_count += 1
                            time_changed_count += 1
                            is_moved = True
                        elif not is_same_time:
                            change_type = "time_only"
                            change_reason = f"Moved time from {b_day} P{b_start} to {d_name} P{start_p}"
                            moved_count += 1
                            time_changed_count += 1
                            is_moved = True
                        else:
                            change_type = "room_only"
                            change_reason = f"Moved room from {b_rid} to {rid} (time slot preserved)"
                            moved_count += 1
                            room_only_count += 1
                            is_moved = True

                        assignment_items.append({
                            "session_id": sid,
                            "course_id": meta.get("course_id"),
                            "faculty_id": meta.get("faculty_id"),
                            "groups": meta.get("groups", []),
                            "original_day": b_day,
                            "original_start_period": b_start,
                            "original_room_id": b_rid,
                            "proposed_day": d_name,
                            "proposed_start_period": start_p,
                            "proposed_room_id": rid,
                            "is_moved": is_moved,
                            "change_type": change_type,
                            "change_reason": change_reason
                        })
                    else:
                        # New session added by disruption
                        moved_count += 1
                        assignment_items.append({
                            "session_id": sid,
                            "course_id": meta.get("course_id"),
                            "faculty_id": meta.get("faculty_id"),
                            "groups": meta.get("groups", []),
                            "original_day": None,
                            "original_start_period": None,
                            "original_room_id": None,
                            "proposed_day": d_name,
                            "proposed_start_period": start_p,
                            "proposed_room_id": rid,
                            "is_moved": True,
                            "change_type": "new_session",
                            "change_reason": "Newly added session allocated by rescheduling engine"
                        })

        # Run independent official validator on proposed timetable
        proposed_schedule_obj = {
            "team": "CIT-DevOps",
            "dataset_id": disrupted_data.get("dataset_id", "cit-public-v1"),
            "sessions": proposed_sessions,
            "exams": baseline_schedule.get("exams", []),
            "fest_week": baseline_schedule.get("fest_week", {})
        }

        val_report = run_official_validator(disrupted_data, proposed_schedule_obj, baseline_schedule)

        return {
            "success": True,
            "solver_status": "OPTIMAL" if status == cp_model.OPTIMAL else "FEASIBLE",
            "solve_time_seconds": solve_duration,
            "sessions_moved": moved_count,
            "time_changed": time_changed_count,
            "room_only_changed": room_only_count,
            "unchanged_sessions": unchanged_count,
            "hard_violations_count": val_report.get("hard_violation_count", 0),
            "hard_violations": val_report.get("hard_violations", []),
            "soft_penalty": val_report.get("soft_total", 0),
            "validation_report": val_report,
            "proposed_sessions": proposed_sessions,
            "assignment_items": assignment_items
        }
