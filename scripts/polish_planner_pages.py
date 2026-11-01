from pathlib import Path

files = [
    Path("frontend/planner.html"),
    Path("frontend/landing.html"),
    Path("public/planner.html"),
    Path("public/landing.html")
]

for f in files:
    if not f.exists():
        continue
    content = f.read_text(encoding="utf-8", errors="ignore")
    
    # Fix broken arrows
    content = content.replace("ENTER WORKSPACE +-", "ENTER WORKSPACE ↗")
    content = content.replace("ENTER CHRONOGRID +-", "ENTER CAMP SCHEDULER ↗")
    content = content.replace("OPEN THE COMMAND CENTRE +-", "OPEN THE COMMAND CENTRE ↗")
    content = content.replace("SEE IT IN THE WORKSPACE +-", "SEE IT IN THE WORKSPACE ↗")
    content = content.replace("Command Centre Login +-", "Command Centre Login ↗")
    content = content.replace("DRAG PENCIL +-", "DRAG PENCIL ↗")
    
    # Enhance top nav links
    old_nav = """        <div class="nav-links">
          <a href="#hero" class="nav-link">01 / THE CAMPUS</a>
          <a href="#rules" class="nav-link">02 / THE RULES</a>
          <a href="/login" class="btn-enter-workspace">ENTER WORKSPACE ↗</a>
        </div>"""
    
    new_nav = """        <div class="nav-links">
          <a href="/" class="nav-link" title="3D WebGL Storytelling Portal">00 / 3D PORTAL</a>
          <a href="#hero" class="nav-link">01 / THE CAMPUS</a>
          <a href="#rules" class="nav-link">02 / THE RULES</a>
          <a href="/solver" class="nav-link" style="color:var(--jade-glow); font-weight:700;" title="CP-SAT Constraint Engine">03 / SOLVER ↗</a>
          <a href="/workspace" class="btn-enter-workspace">ENTER WORKSPACE ↗</a>
        </div>"""
        
    if old_nav in content:
        content = content.replace(old_nav, new_nav)
    else:
        # Fallback replacement
        content = content.replace(
            '<a href="#rules" class="nav-link">02 / THE RULES</a>',
            '<a href="#rules" class="nav-link">02 / THE RULES</a>\n          <a href="/solver" class="nav-link" style="color:var(--jade-glow); font-weight:700;" title="CP-SAT Constraint Engine">03 / SOLVER ↗</a>'
        )
        content = content.replace('href="/login" class="btn-enter-workspace"', 'href="/workspace" class="btn-enter-workspace"')
    
    # Save back
    f.write_text(content, encoding="utf-8")
    print(f"Polished {f}")
