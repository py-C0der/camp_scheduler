import re
from pathlib import Path

p = Path("backend/main.py")
text = p.read_text(encoding="utf-8")

if "def serve_solver():" in text:
    print("serve_solver already exists in backend/main.py")
else:
    pattern = r'(def serve_planner\(\):[\s\S]*?return FileResponse\(FRONTEND_DIR / "index\.html"\))'
    match = re.search(pattern, text)
    if match:
        solver_code = """

@app.get("/solver", response_class=HTMLResponse)
@app.get("/solver.html", response_class=HTMLResponse)
@app.get("/autonomous", response_class=HTMLResponse)
def serve_solver():
    solver_file = FRONTEND_DIR / "solver.html"
    if not solver_file.exists():
        solver_file = Path(__file__).resolve().parent.parent / "public" / "solver.html"
    if solver_file.exists():
        return FileResponse(solver_file)
    return FileResponse(FRONTEND_DIR / "index.html")"""
        new_text = text[:match.end()] + solver_code + text[match.end():]
        p.write_text(new_text, encoding="utf-8")
        print("Successfully added serve_solver to backend/main.py!")
    else:
        print("Could not find serve_planner block to attach after!")
