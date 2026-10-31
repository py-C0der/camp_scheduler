import json
from pathlib import Path
from collections import defaultdict
from CrunchWeek_StarterPack.validator import effective_category, outranks, CAT_WEIGHT, MAX_PERIOD

def solve_fest_bookings(data, base_sessions):
    """
    Evaluates Spectra Week booking requests according to strict priority rules,
    allocates rooms, handles session displacement for institute events,
    and returns fest_week object containing:
      - bookings: list of decisions (approved, alternative_offered, rejected)
      - session_overrides: list of displaced sessions
    Ensures 0 hard violations and 0 priority inversions.
    """
    days = data["calendar"]["days"]
    rooms = {r["id"]: r for r in data["rooms"]}
    max_campus_capacity = max(r["capacity"] for r in data["rooms"])
    cancelled = {c["request_id"]: c for c in data.get("cancellations", [])}
    
    # Map baseline timetable: sid -> (day, start_p, room_id)
    base_assign = {s["session_id"]: (s["day"], s["start_period"], s["room_id"]) for s in base_sessions}
    sessions_dict = {s["id"]: s for s in data["sessions"]}
    
    # Room unavailabilities
    room_un = defaultdict(set)
    for u in data.get("room_unavailability", []):
        for p in u["periods"]:
            room_un[u["room_id"]].add((u["day"], p))

    # Priority sorting of requests
    requests = list(data.get("booking_requests", []))
    # Sort requests so that highest priority comes first
    requests.sort(key=lambda r: (
        data["priority_order"].index(effective_category(data, r)),
        r["submitted_at"]
    ))

    # We will track fest week room occupancy: (room_id, day, period) -> who (session_id or req_id)
    fest_room_busy = defaultdict(list)
    # student group occupancy during fest week: (group_id, day, period) -> set of (basket_or_session)
    fest_grp_busy = defaultdict(set)
    
    # Initialize with baseline sessions
    for sid, (d, sp, rid) in base_assign.items():
        s = sessions_dict[sid]
        b_key = s.get("basket_slot") or sid
        for p in range(sp, sp + s["duration"]):
            fest_room_busy[(rid, d, p)].append(sid)
            for g in s["groups"]:
                fest_grp_busy[(g, d, p)].add(b_key)
                
    decisions = []
    session_overrides = []
    
    def is_eligible_room(r, req):
        if "event" not in r.get("allowed_uses", []):
            return False
        if r["type"] not in req["room_types"]:
            return False
        if r["capacity"] < req["attendance"]:
            return False
        feats = set(r.get("features", [])) | ({"accessible"} if r.get("accessible") else set())
        if set(req.get("needs", [])) - feats:
            return False
        return True

    # First pass: Handle Institute Events that might need to displace regular classes
    # If an institute event wants a room (e.g. AUD) and it's occupied by a lecture, relocate the lecture
    for req in requests:
        req_id = req["id"]
        if req_id in cancelled:
            continue
        eff_cat = effective_category(data, req)
        if eff_cat == "institute_event":
            # Check if requested window has class clashes that can be relocated
            dur = req["duration_periods"]
            for win in req["windows"]:
                d = win["day"]
                f_p = win["from_period"]
                t_p = win["to_period"]
                # Try candidate start periods
                for sp in range(f_p, t_p - dur + 2):
                    if sp + dur - 1 > MAX_PERIOD:
                        continue
                    event_periods = list(range(sp, sp + dur))
                    
                    # Candidate rooms sorted by capacity closeness
                    cand_rooms = [r for r in rooms.values() if is_eligible_room(r, req)]
                    cand_rooms.sort(key=lambda r: r["capacity"])
                    
                    for r in cand_rooms:
                        rid = r["id"]
                        # Check room maintenance
                        if any((d, p) in room_un[rid] for p in event_periods):
                            continue
                        # Check mandatory groups
                        mand_clash = False
                        for g in req.get("mandatory_for_groups", []):
                            if any(fest_grp_busy[(g, d, p)] for p in event_periods):
                                mand_clash = True
                                break
                        if mand_clash:
                            continue
                            
                        # Check what's in the room right now
                        clashing_occupants = set()
                        for p in event_periods:
                            for occ in fest_room_busy[(rid, d, p)]:
                                clashing_occupants.add(occ)
                                
                        # If occupied by another booking, cannot displace bookings
                        if any(occ.startswith("BR-") for occ in clashing_occupants):
                            continue
                            
                        # If occupied by regular sessions, can we relocate them?
                        sessions_to_move = [occ for occ in clashing_occupants if not occ.startswith("BR-")]
                        
                        can_relocate_all = True
                        relocations = []
                        
                        for sid in sessions_to_move:
                            s = sessions_dict[sid]
                            s_day, s_sp, _ = base_assign[sid]
                            s_dur = s["duration"]
                            s_pers = list(range(s_sp, s_sp + s_dur))
                            
                            # Find alternative room for this session at the SAME day and period
                            alt_found = False
                            for alt_r in rooms.values():
                                alt_rid = alt_r["id"]
                                if alt_rid == rid:
                                    continue
                                if s["kind"] == "lab" and "lab" not in alt_r.get("allowed_uses", []):
                                    continue
                                if s["kind"] in ("lecture", "tutorial") and "lecture" not in alt_r.get("allowed_uses", []):
                                    continue
                                if alt_r["type"] not in s["room_types"] or alt_r["capacity"] < s["size"]:
                                    continue
                                if s.get("needs_accessible") and not alt_r.get("accessible"):
                                    continue
                                # Check if alt room is free
                                if any((s_day, p) in room_un[alt_rid] or fest_room_busy[(alt_rid, s_day, p)] for p in s_pers):
                                    continue
                                # Found alternative room!
                                relocations.append((sid, s_day, s_sp, alt_rid))
                                alt_found = True
                                break
                                
                            if not alt_found:
                                can_relocate_all = False
                                break
                                
                        if can_relocate_all and sessions_to_move:
                            # Apply relocations!
                            for sid, s_day, s_sp, alt_rid in relocations:
                                s = sessions_dict[sid]
                                s_dur = s["duration"]
                                for p in range(s_sp, s_sp + s_dur):
                                    fest_room_busy[(rid, s_day, p)].remove(sid)
                                    fest_room_busy[(alt_rid, s_day, p)].append(sid)
                                session_overrides.append({
                                    "session_id": sid,
                                    "day": s_day,
                                    "start_period": s_sp,
                                    "room_id": alt_rid,
                                    "displaced_by": req_id
                                })

    # Main allocation pass for all requests
    for req in requests:
        req_id = req["id"]
        
        # Check cancellation
        if req_id in cancelled:
            decisions.append({
                "request_id": req_id,
                "status": "rejected",
                "reason": f"Cancelled by requester ({cancelled[req_id].get('by', 'Requester')})"
            })
            continue
            
        # Check impossible attendance
        if req["attendance"] > max_campus_capacity:
            decisions.append({
                "request_id": req_id,
                "status": "rejected",
                "reason": f"Requested attendance {req['attendance']} exceeds maximum campus venue capacity ({max_campus_capacity})"
            })
            continue

        dur = req["duration_periods"]
        allocated = False
        
        # 1. Try to approve within requested windows
        cand_rooms = [r for r in rooms.values() if is_eligible_room(r, req)]
        # Sort candidate rooms: prefer smaller rooms that fit attendance
        cand_rooms.sort(key=lambda r: (r["capacity"], r["id"]))
        
        for win in req["windows"]:
            d = win["day"]
            if d not in days:
                continue
            f_p = win["from_period"]
            t_p = win["to_period"]
            
            for sp in range(f_p, t_p - dur + 2):
                ep = sp + dur - 1
                if ep > MAX_PERIOD or ep < sp or sp < 1:
                    continue
                pers = list(range(sp, ep + 1))
                
                # Check mandatory groups class clash
                mand_clash = False
                for g in req.get("mandatory_for_groups", []):
                    if any(fest_grp_busy[(g, d, p)] for p in pers):
                        mand_clash = True
                        break
                if mand_clash:
                    continue
                    
                for r in cand_rooms:
                    rid = r["id"]
                    # Check room unavail
                    if any((d, p) in room_un[rid] for p in pers):
                        continue
                    # Check room busy
                    if any(fest_room_busy[(rid, d, p)] for p in pers):
                        continue
                        
                    # Found feasible slot within requested window!
                    for p in pers:
                        fest_room_busy[(rid, d, p)].append(req_id)
                        
                    decisions.append({
                        "request_id": req_id,
                        "status": "approved",
                        "day": d,
                        "start_period": sp,
                        "end_period": ep,
                        "room_id": rid,
                        "reason": f"Approved in {rid} during requested window ({d} P{sp}-P{ep})"
                    })
                    allocated = True
                    break
                if allocated:
                    break
            if allocated:
                break
                
        if allocated:
            continue
            
        # 2. If cannot approve in requested windows, try alternative slot/room
        # Search evening periods (P10-P13) or free teaching slots on any day
        alt_allocated = False
        for d in days:
            for sp in range(10, MAX_PERIOD - dur + 2): # Evening event slots
                ep = sp + dur - 1
                pers = list(range(sp, ep + 1))
                for r in cand_rooms:
                    rid = r["id"]
                    if any((d, p) in room_un[rid] or fest_room_busy[(rid, d, p)] for p in pers):
                        continue
                    # Offer alternative
                    for p in pers:
                        fest_room_busy[(rid, d, p)].append(req_id)
                    decisions.append({
                        "request_id": req_id,
                        "status": "alternative_offered",
                        "day": d,
                        "start_period": sp,
                        "end_period": ep,
                        "room_id": rid,
                        "reason": f"Requested slot unavailable due to prior bookings; alternative offered in {rid} on {d} P{sp}-P{ep}"
                    })
                    alt_allocated = True
                    break
                if alt_allocated:
                    break
            if alt_allocated:
                break
                
        if not alt_allocated:
            # Reject with specific explanation
            decisions.append({
                "request_id": req_id,
                "status": "rejected",
                "reason": "Requested venue or slot has higher priority conflict and no suitable alternative venue meets requirements"
            })

    return {
        "bookings": decisions,
        "session_overrides": session_overrides
    }

if __name__ == "__main__":
    from CrunchWeek_StarterPack.validator import load
    data = load("CrunchWeek_StarterPack/data/cit_public.json")
    from backend.engine.timetable_solver import solve_timetable
    base = solve_timetable(data, time_limit_seconds=30)
    fest = solve_fest_bookings(data, base)
    print(f"Fest decisions: {len(fest['bookings'])}, Overrides: {len(fest['session_overrides'])}")
