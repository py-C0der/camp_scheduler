# Patch decision_evidence_service.py
with open("backend/services/decision_evidence_service.py", "r", encoding="utf-8") as f:
    text = f.read()

target = '''        s = self.sessions.get(session_id)
        if not s:
            return {
                "is_feasible": False,'''

replacement = '''        s = self.sessions.get(session_id)
        if not s:
            return {
                "session_id": session_id,
                "is_feasible": False,'''

if target in text:
    text = text.replace(target, replacement)
    with open("backend/services/decision_evidence_service.py", "w", encoding="utf-8") as f:
        f.write(text)
    print("Patched decision_evidence_service.py!")
else:
    print("Pattern not found in decision_evidence_service.py")

# Patch assistant.py
with open("backend/ai/assistant.py", "r", encoding="utf-8") as f:
    text2 = f.read()

target2 = "msg = f\"Analysis for moving session {cf['session_id']} to {target_day}:\\n\\n\""
replacement2 = "msg = f\"Analysis for moving session {cf.get('session_id', session_id)} to {target_day}:\\n\\n\""

if target2 in text2:
    text2 = text2.replace(target2, replacement2)
    with open("backend/ai/assistant.py", "w", encoding="utf-8") as f:
        f.write(text2)
    print("Patched assistant.py!")
else:
    print("Pattern not found in assistant.py")
