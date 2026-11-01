import re
from pathlib import Path

# 1. Update backend/main.py
main_path = Path("backend/main.py")
text = main_path.read_text(encoding="utf-8")

# Replace serve_root to directly serve index.html
old_serve_root = re.compile(
    r'@app\.get\("/"[^\n]*\n(?:@app\.get\([^\n]*\n)*def serve_root\(\):[\s\S]*?return FileResponse\([^\)]+\)',
    re.MULTILINE
)

new_serve_root = '''@app.get("/", response_class=HTMLResponse)
@app.get("/workspace", response_class=HTMLResponse)
@app.get("/workspace.html", response_class=HTMLResponse)
@app.get("/app", response_class=HTMLResponse)
def serve_root():
    index_file = FRONTEND_DIR / "index.html"
    if not index_file.exists():
        index_file = Path(__file__).resolve().parent.parent / "public" / "index.html"
    return FileResponse(index_file)'''

if old_serve_root.search(text):
    text = old_serve_root.sub(new_serve_root, text)
    print("Replaced serve_root in backend/main.py to directly serve index.html!")
else:
    print("Could not regex match serve_root, checking manual replacement...")

main_path.write_text(text, encoding="utf-8")

# 2. Remove "Public Landing" link from all index.html files
for p in [Path("frontend/index.html"), Path("public/index.html")]:
    if p.exists():
        c = p.read_text(encoding="utf-8")
        # Remove Public Landing nav li
        c = re.sub(r'<li[^>]*>\s*<a href="/"[^>]*>.*?Public Landing.*?</a>\s*</li>', '', c, flags=re.IGNORECASE | re.DOTALL)
        p.write_text(c, encoding="utf-8")
        print(f"Removed Public Landing link from {p}")

print("Clean and simple root routing updated!")
