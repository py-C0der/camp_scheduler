from pathlib import Path

gpu_css_planner = """
    /* ========================================================
       GPU HARDWARE ACCELERATION & COMPOSITOR OPTIMIZATIONS
       ======================================================== */
    * {
      -webkit-font-smoothing: antialiased;
      -moz-osx-font-smoothing: grayscale;
    }

    .planner-3d-viewport,
    .planner-desk-book,
    .left-info-card,
    .sticky-note-realistic,
    .hero-center-stage,
    .edge-spine {
      transform: translate3d(0, 0, 0);
      -webkit-transform: translate3d(0, 0, 0);
      backface-visibility: hidden;
      -webkit-backface-visibility: hidden;
      perspective: 1200px;
      -webkit-perspective: 1200px;
      transform-style: preserve-3d;
      -webkit-transform-style: preserve-3d;
      will-change: transform, opacity;
    }
"""

gpu_css_intro = """
    /* GPU Hardware Accelerated Viewport Layer */
    canvas, #webgl, .pre-canvas-wrap, .hud-wrap {
      transform: translate3d(0, 0, 0) !important;
      -webkit-transform: translate3d(0, 0, 0) !important;
      backface-visibility: hidden !important;
      -webkit-backface-visibility: hidden !important;
      will-change: transform, opacity !important;
    }
"""

# Apply to planner.html and landing.html
for p in [Path("frontend/planner.html"), Path("public/planner.html"), Path("frontend/landing.html"), Path("public/landing.html")]:
    if p.exists():
        with open(p, "r", encoding="utf-8") as f:
            content = f.read()
        if "GPU HARDWARE ACCELERATION" not in content:
            pos = content.find("</style>")
            if pos != -1:
                content = content[:pos] + "\n" + gpu_css_planner + "\n" + content[pos:]
                with open(p, "w", encoding="utf-8") as f:
                    f.write(content)
                print(f"Applied GPU optimizations to {p}!")

# Apply to intro.html
for p in [Path("frontend/intro.html"), Path("public/intro.html")]:
    if p.exists():
        with open(p, "r", encoding="utf-8") as f:
            content = f.read()
        if "GPU Hardware Accelerated Viewport Layer" not in content:
            pos = content.find("</style>")
            if pos != -1:
                content = content[:pos] + "\n" + gpu_css_intro + "\n" + content[pos:]
                with open(p, "w", encoding="utf-8") as f:
                    f.write(content)
                print(f"Applied GPU optimizations to {p}!")
