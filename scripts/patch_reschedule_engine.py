with open("backend/disruptions/reschedule_engine.py", "r", encoding="utf-8") as f:
    text = f.read()

old_str = 'if b.get("status") == "approved" and b.get("room_id") and b.get("day") in day_to_idx:'
new_str = 'if b.get("status") in ("approved", "alternative_offered") and b.get("room_id") and b.get("day") in day_to_idx:'

if old_str in text:
    text = text.replace(old_str, new_str)
    with open("backend/disruptions/reschedule_engine.py", "w", encoding="utf-8") as f:
        f.write(text)
    print("Successfully patched backend/disruptions/reschedule_engine.py!")
elif new_str in text:
    print("reschedule_engine.py is already patched!")
else:
    print("Warning: Pattern not found in reschedule_engine.py")
