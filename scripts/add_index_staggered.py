from pathlib import Path

index_paths = [Path("frontend/index.html"), Path("public/index.html")]

index_anim_css = """
    /* ========================================================
       ONE-AFTER-ANOTHER STAGGERED ENTRANCE ANIMATIONS
       ======================================================== */
    @keyframes staggerCardIn {
      0% {
        opacity: 0;
        transform: translateY(20px) scale(0.97);
      }
      100% {
        opacity: 1;
        transform: translateY(0) scale(1);
      }
    }

    .kpi-row .kpi-card:nth-child(1) { animation: staggerCardIn 0.5s cubic-bezier(0.16, 1, 0.3, 1) 0.05s both; }
    .kpi-row .kpi-card:nth-child(2) { animation: staggerCardIn 0.5s cubic-bezier(0.16, 1, 0.3, 1) 0.12s both; }
    .kpi-row .kpi-card:nth-child(3) { animation: staggerCardIn 0.5s cubic-bezier(0.16, 1, 0.3, 1) 0.19s both; }
    .kpi-row .kpi-card:nth-child(4) { animation: staggerCardIn 0.5s cubic-bezier(0.16, 1, 0.3, 1) 0.26s both; }
    .kpi-row .kpi-card:nth-child(5) { animation: staggerCardIn 0.5s cubic-bezier(0.16, 1, 0.3, 1) 0.33s both; }
    .kpi-row .kpi-card:nth-child(6) { animation: staggerCardIn 0.5s cubic-bezier(0.16, 1, 0.3, 1) 0.40s both; }
    .kpi-row .kpi-card:nth-child(7) { animation: staggerCardIn 0.5s cubic-bezier(0.16, 1, 0.3, 1) 0.47s both; }

    .panel-card {
      animation: staggerCardIn 0.6s cubic-bezier(0.16, 1, 0.3, 1) 0.2s both;
    }
"""

for p in index_paths:
    if p.exists():
        with open(p, "r", encoding="utf-8") as f:
            content = f.read()

        if "staggerCardIn" not in content:
            pos = content.find("</style>")
            if pos != -1:
                content = content[:pos] + "\n" + index_anim_css + "\n" + content[pos:]
                with open(p, "w", encoding="utf-8") as f:
                    f.write(content)
                print(f"Added staggered animations to {p}!")
