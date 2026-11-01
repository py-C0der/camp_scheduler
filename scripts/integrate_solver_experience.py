import os
from pathlib import Path

src = Path("iit bhubanaswar/CIT_CAMPscheduler_Complete_Project/campscheduler-solver/index.html")
if not src.exists():
    print("Source not found:", src)
    exit(1)

text = src.read_text(encoding="utf-8", errors="ignore")

# Fix audio icon glyphs
text = text.replace('id="audio-icon-glyph">dY"', 'id="audio-icon-glyph">🔊')
text = text.replace('dY"', '🔊')

# Add navigation items for Planner and Workspace in hud-navigation
replacement_nav = """<a class="hud-nav-item" href="#console" onclick="synthesizeSound(720)">Live Solver</a>
      <a class="hud-nav-item" href="/planner" style="color:#34d399; font-weight:700;">Digital Planner ↗</a>
      <a class="hud-nav-item" href="/workspace" style="color:#6ee7b7; font-weight:700;">Command Workspace ↗</a>"""

if 'href="#console" onclick="synthesizeSound(720)">Live Solver</a>' in text:
    text = text.replace('href="#console" onclick="synthesizeSound(720)">Live Solver</a>', replacement_nav)
    print("Enhanced nav with Planner and Workspace links!")

# Ensure WebGL renderer uses high-performance GPU
if 'new THREE.WebGLRenderer({ canvas: canvas, alpha: true })' in text:
    text = text.replace(
        'new THREE.WebGLRenderer({ canvas: canvas, alpha: true })',
        'new THREE.WebGLRenderer({ canvas: canvas, alpha: true, powerPreference: "high-performance", antialias: false })'
    )
    print("Applied powerPreference: high-performance to Three.js WebGL renderer!")

# Write to frontend and public
Path("frontend/solver.html").write_text(text, encoding="utf-8")
Path("public/solver.html").write_text(text, encoding="utf-8")
print("Saved frontend/solver.html and public/solver.html successfully!")
