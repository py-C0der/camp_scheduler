from pathlib import Path

cluster_html = """      <!-- Direct links to CAMP SCHEDULER Planner, Solver & Workspace -->
      <div style="position:fixed; top:24px; right:24px; z-index:99999; display:flex; gap:10px; align-items:center; flex-wrap:wrap;">
        <a href="/planner" style="background:#1A6E48; color:#FFFFFF; font-family:'JetBrains Mono', monospace; font-size:12px; font-weight:800; letter-spacing:0.06em; padding:9px 18px; border-radius:30px; text-decoration:none; border:1.5px solid #42FFB7; box-shadow:0 4px 18px rgba(0,0,0,0.45); display:inline-flex; align-items:center; gap:6px; transition:all 0.18s ease;" onmouseover="this.style.background='#145738'; this.style.transform='translateY(-2px)';" onmouseout="this.style.background='#1A6E48'; this.style.transform='translateY(0)';">
          <span>DIGITAL PLANNER</span>
          <span>↗</span>
        </a>
        <a href="/solver" style="background:rgba(10,31,22,0.92); color:#42FFB7; font-family:'JetBrains Mono', monospace; font-size:12px; font-weight:800; letter-spacing:0.06em; padding:9px 18px; border-radius:30px; text-decoration:none; border:1.5px solid #34d399; box-shadow:0 4px 18px rgba(0,0,0,0.45); display:inline-flex; align-items:center; gap:6px; transition:all 0.18s ease;" onmouseover="this.style.background='#10b981'; this.style.color='#020604'; this.style.transform='translateY(-2px)';" onmouseout="this.style.background='rgba(10,31,22,0.92)'; this.style.color='#42FFB7'; this.style.transform='translateY(0)';">
          <span>CP-SAT SOLVER</span>
          <span>↗</span>
        </a>
        <a href="/workspace" style="background:#262424; color:#FFFFFF; font-family:'JetBrains Mono', monospace; font-size:12px; font-weight:800; letter-spacing:0.06em; padding:9px 18px; border-radius:30px; text-decoration:none; border:1.5px solid rgba(255,255,255,0.35); box-shadow:0 4px 18px rgba(0,0,0,0.45); display:inline-flex; align-items:center; gap:6px; transition:all 0.18s ease;" onmouseover="this.style.background='#3f3c3d'; this.style.transform='translateY(-2px)';" onmouseout="this.style.background='#262424'; this.style.transform='translateY(0)';">
          <span>WORKSPACE</span>
          <span>↗</span>
        </a>
      </div>"""

for p in ["frontend/intro.html", "public/intro.html"]:
    path = Path(p)
    if not path.exists():
        continue
    content = path.read_text(encoding="utf-8", errors="ignore")
    import re
    # Replace any existing button container
    pattern = r'<!-- Direct link to CAMP SCHEDULER Planner & Workspace -->[\s\S]*?</div>\s*</div>'
    if re.search(pattern, content):
        content = re.sub(pattern, cluster_html, content)
        print(f"Replaced button cluster in {p}")
    elif "DIGITAL PLANNER" not in content:
        content = content.replace("</body>", cluster_html + "\n</body>")
        print(f"Appended button cluster in {p}")
    path.write_text(content, encoding="utf-8")
