import os, shutil
from pathlib import Path

src_landing = Path("iit bhubanaswar/CIT_CAMPscheduler_Complete_Project/landing-page")
src_assets = src_landing / "assets"
src_vendor = src_landing / "vendor"
src_intro = src_landing / "index.html"

dst_assets = Path("assets")
dst_vendor = Path("vendor")

if src_assets.exists():
    if dst_assets.exists():
        shutil.rmtree(dst_assets)
    shutil.copytree(src_assets, dst_assets)
    print("Copied assets/ to root")

if src_vendor.exists():
    if dst_vendor.exists():
        shutil.rmtree(dst_vendor)
    shutil.copytree(src_vendor, dst_vendor)
    print("Copied vendor/ to root")

# Also copy into public/ so static file servers can find them under /assets or /public/assets
pub_assets = Path("public/assets")
if pub_assets.exists():
    shutil.rmtree(pub_assets)
shutil.copytree(dst_assets, pub_assets)

pub_vendor = Path("public/vendor")
if pub_vendor.exists():
    shutil.rmtree(pub_vendor)
shutil.copytree(dst_vendor, pub_vendor)
print("Copied assets and vendor to public/")

# Update main-BYq3OzcY.js to ensure links go to /planner
for js_file in [dst_assets / "main-BYq3OzcY.js", pub_assets / "main-BYq3OzcY.js"]:
    if js_file.exists():
        txt = js_file.read_text(encoding="utf-8", errors="ignore")
        txt = txt.replace("window.location.href=`http://127.0.0.1:8000/`", "window.location.href=`/planner`")
        txt = txt.replace('href="http://127.0.0.1:8000/"', 'href="/planner"')
        js_file.write_text(txt, encoding="utf-8")
print("Updated main-BYq3OzcY.js redirect urls")

# Copy intro.html
with open(src_intro, "r", encoding="utf-8") as f:
    intro_html = f.read()

skip_btn = """
    <!-- Direct link to CAMP SCHEDULER Planner & Workspace -->
    <div style="position:fixed; top:24px; right:24px; z-index:99999; display:flex; gap:12px; align-items:center;">
      <a href="/planner" style="background:#1A6E48; color:#FFFFFF; font-family:'JetBrains Mono', monospace; font-size:12px; font-weight:800; letter-spacing:0.06em; padding:10px 20px; border-radius:30px; text-decoration:none; border:1.5px solid #42FFB7; box-shadow:0 4px 18px rgba(0,0,0,0.45); display:inline-flex; align-items:center; gap:8px; transition:transform 0.15s, background 0.15s;" onmouseover="this.style.background='#145738'; this.style.transform='translateY(-2px)';" onmouseout="this.style.background='#1A6E48'; this.style.transform='translateY(0)';">
        <span>ENTER CAMP SCHEDULER</span>
        <span>&rarr;</span>
      </a>
    </div>
"""
if "ENTER CAMP SCHEDULER" not in intro_html:
    intro_html = intro_html.replace("</body>", skip_btn + "\n</body>")

for p in ["frontend/intro.html", "public/intro.html"]:
    with open(p, "w", encoding="utf-8") as f:
        f.write(intro_html)
print("Saved intro.html in frontend/ and public/")

# Copy planner.html & landing.html
src_planner = Path("iit bhubanaswar/CIT_CAMPscheduler_Complete_Project/camp_scheduler_app/frontend/planner.html")
if not src_planner.exists():
    src_planner = Path("iit bhubanaswar/IITBBSR (1)/IITBBSR/frontend/planner.html")
if src_planner.exists():
    with open(src_planner, "r", encoding="utf-8") as f:
        pl_html = f.read()
    for p in ["frontend/planner.html", "public/planner.html", "frontend/landing.html", "public/landing.html"]:
        with open(p, "w", encoding="utf-8") as f:
            f.write(pl_html)
    print("Saved planner.html and landing.html")
