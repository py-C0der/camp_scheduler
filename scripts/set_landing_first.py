with open("backend/main.py", "r", encoding="utf-8") as f:
    text = f.read()

target = """@app.get("/", response_class=HTMLResponse)
def serve_root():
    intro_file = FRONTEND_DIR / "intro.html"
    if not intro_file.exists():
        intro_file = Path(__file__).resolve().parent.parent / "public" / "intro.html"
    if intro_file.exists():
        return FileResponse(intro_file)
    planner_file = FRONTEND_DIR / "planner.html"
    if not planner_file.exists():
        planner_file = Path(__file__).resolve().parent.parent / "public" / "planner.html"
    if planner_file.exists():
        return FileResponse(planner_file)
    return FileResponse(FRONTEND_DIR / "index.html")"""

replacement = """@app.get("/", response_class=HTMLResponse)
def serve_root():
    planner_file = FRONTEND_DIR / "planner.html"
    if not planner_file.exists():
        planner_file = FRONTEND_DIR / "landing.html"
    if not planner_file.exists():
        planner_file = Path(__file__).resolve().parent.parent / "public" / "planner.html"
    if planner_file.exists():
        return FileResponse(planner_file)
    return FileResponse(FRONTEND_DIR / "index.html")"""

if target in text:
    text = text.replace(target, replacement)
    print("Updated serve_root to serve landing / planner page first!")
else:
    normalized = text.replace("\r\n", "\n")
    if target in normalized:
        normalized = normalized.replace(target, replacement)
        text = normalized
        print("Updated serve_root with normalized newlines!")
    else:
        print("Target not found directly.")

with open("backend/main.py", "w", encoding="utf-8") as f:
    f.write(text)
