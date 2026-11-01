with open("backend/main.py", "r", encoding="utf-8") as f:
    text = f.read()

target = 'return HTMLResponse("<h1>CIT Campus Operations API is Live. Visit /docs for OpenAPI specs.</h1>")'
assert target in text, "target string not found in backend/main.py"

routes_code = """return HTMLResponse("<h1>CIT Campus Operations API is Live. Visit /docs for OpenAPI specs.</h1>")


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

text = text.replace(target, routes_code, 1)

with open("backend/main.py", "w", encoding="utf-8") as f:
    f.write(text)

print("Successfully inserted multi-page routes into backend/main.py")
