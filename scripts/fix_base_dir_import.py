with open("backend/main.py", "r", encoding="utf-8") as f:
    text = f.read()

old_imp = "from backend.config import DATA_PATH, DISRUPTION_PATH, EXPORTS_DIR, FRONTEND_DIR"
new_imp = "from backend.config import BASE_DIR, DATA_PATH, DISRUPTION_PATH, EXPORTS_DIR, FRONTEND_DIR"

if old_imp in text:
    text = text.replace(old_imp, new_imp)
    with open("backend/main.py", "w", encoding="utf-8") as f:
        f.write(text)
    print("Added BASE_DIR to import in backend/main.py!")
else:
    print("Could not find import statement")
