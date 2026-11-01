with open("backend/main.py", "r", encoding="utf-8") as f:
    code = f.read()

target = """@app.get("/", response_class=HTMLResponse)
def serve_index():
    index_file = FRONTEND_DIR / "index.html"
    if not index_file.exists():
        index_file = Path(__file__).resolve().parent.parent / "public" / "index.html"
    if index_file.exists():
        return FileResponse(index_file)
    return HTMLResponse("<h1>Antigravity Backend Running</h1>", status_code=200)"""

addition = """@app.get("/", response_class=HTMLResponse)
def serve_index():
    index_file = FRONTEND_DIR / "index.html"
    if not index_file.exists():
        index_file = Path(__file__).resolve().parent.parent / "public" / "index.html"
    if index_file.exists():
        return FileResponse(index_file)
    return HTMLResponse("<h1>Antigravity Backend Running</h1>", status_code=200)

# Multi-Page Application Dedicated Routes
PAGE_NAMES = [
    "dashboard", "timetable", "validations", "examinations",
    "bookings", "disruptions", "notifications", "ai-assistant", "login"
]

def _create_page_endpoint(p_name: str):
    def page_endpoint():
        p_path = FRONTEND_DIR / f"{p_name}.html"
        if not p_path.exists():
            p_path = Path(__file__).resolve().parent.parent / "public" / f"{p_name}.html"
        if p_path.exists():
            return FileResponse(p_path)
        return FileResponse(FRONTEND_DIR / "index.html")
    return page_endpoint

for page_name in PAGE_NAMES:
    app.add_api_route(f"/{page_name}", _create_page_endpoint(page_name), methods=["GET"], response_class=HTMLResponse)
    app.add_api_route(f"/{page_name}.html", _create_page_endpoint(page_name), methods=["GET"], response_class=HTMLResponse)
"""

norm_code = code.replace("\r\n", "\n")
norm_target = target.replace("\r\n", "\n")

if norm_target not in norm_code:
    # Let's inspect serve_index in code
    import re
    m = re.search(r'@app\.get\("/"[^)]*\)\s*def serve_index\(\):.*?(?=return HTMLResponse[^\n]*\n)', norm_code, re.DOTALL)
    if m:
        full_match = m.group(0) + "return HTMLResponse(\"<h1>Antigravity Backend Running</h1>\", status_code=200)"
        norm_code = norm_code.replace(full_match, addition.replace("\r\n", "\n"), 1)
        print("Replaced with regex pattern")
    else:
        print("Error: serve_index pattern not matched")
else:
    norm_code = norm_code.replace(norm_target, addition.replace("\r\n", "\n"), 1)
    print("Replaced directly")

with open("backend/main.py", "w", encoding="utf-8") as f:
    f.write(norm_code.replace("\n", "\r\n"))

print("Added page routes to backend/main.py")
