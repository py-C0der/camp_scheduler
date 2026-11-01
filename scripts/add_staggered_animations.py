from pathlib import Path

planner_paths = [
    Path("frontend/planner.html"),
    Path("public/planner.html"),
    Path("frontend/landing.html"),
    Path("public/landing.html")
]

staggered_css = """
    /* ========================================================
       ONE-AFTER-ANOTHER STAGGERED ENTRANCE ANIMATIONS
       ======================================================== */
    @keyframes cascadeFadeUp {
      0% {
        opacity: 0;
        transform: translateY(32px) scale(0.96);
      }
      65% {
        opacity: 0.95;
        transform: translateY(-3px) scale(1.008);
      }
      100% {
        opacity: 1;
        transform: translateY(0) scale(1);
      }
    }

    @keyframes cardSlideLeft {
      0% {
        opacity: 0;
        transform: translateX(-45px);
      }
      100% {
        opacity: 1;
        transform: translateX(0);
      }
    }

    @keyframes dropTapeSticker {
      0% {
        opacity: 0;
        transform: translateY(-50px) rotate(-14deg) scale(0.8);
      }
      70% {
        opacity: 1;
        transform: translateY(6px) rotate(3deg) scale(1.03);
      }
      100% {
        opacity: 1;
        transform: translateY(0) rotate(-1.5deg) scale(1);
      }
    }

    @keyframes floatPlanner {
      0%, 100% {
        transform: translateY(0px) rotateX(16deg) rotateY(-8deg) rotateZ(1deg);
      }
      50% {
        transform: translateY(-10px) rotateX(18deg) rotateY(-6deg) rotateZ(1.5deg);
      }
    }

    @keyframes pulseGlowEmerald {
      0%, 100% {
        box-shadow: 0 10px 30px rgba(0,0,0,0.35), 0 0 15px rgba(66, 255, 183, 0.25);
      }
      50% {
        box-shadow: 0 14px 40px rgba(0,0,0,0.45), 0 0 30px rgba(66, 255, 183, 0.55);
      }
    }

    /* Staggered One-After-Another Delays */
    .hero-top-meta {
      animation: cascadeFadeUp 0.6s cubic-bezier(0.16, 1, 0.3, 1) 0.08s both;
    }
    .hero-pretitle {
      animation: cascadeFadeUp 0.6s cubic-bezier(0.16, 1, 0.3, 1) 0.18s both;
    }
    .hero-title-giant {
      animation: cascadeFadeUp 0.7s cubic-bezier(0.16, 1, 0.3, 1) 0.28s both;
    }
    .hero-subtitle-sync {
      animation: cascadeFadeUp 0.65s cubic-bezier(0.16, 1, 0.3, 1) 0.4s both;
    }
    .left-info-card {
      animation: cardSlideLeft 0.75s cubic-bezier(0.16, 1, 0.3, 1) 0.52s both, pulseGlowEmerald 4s ease-in-out 1.3s infinite;
    }
    .planner-3d-viewport {
      animation: cascadeFadeUp 0.85s cubic-bezier(0.16, 1, 0.3, 1) 0.68s both;
    }
    .planner-desk-book {
      animation: floatPlanner 6s ease-in-out infinite 1.5s;
    }
    .sticky-note-realistic {
      animation: dropTapeSticker 0.8s cubic-bezier(0.34, 1.56, 0.64, 1) 0.85s both;
      cursor: pointer;
      transition: transform 0.2s cubic-bezier(0.34, 1.56, 0.64, 1), box-shadow 0.2s;
    }
    .sticky-note-realistic:hover {
      transform: translateY(-8px) rotate(-3deg) scale(1.05) !important;
      box-shadow: 0 16px 32px rgba(0,0,0,0.4) !important;
    }
"""

for p in planner_paths:
    if p.exists():
        with open(p, "r", encoding="utf-8") as f:
            content = f.read()

        if "cascadeFadeUp" not in content:
            pos = content.find("</style>")
            if pos != -1:
                content = content[:pos] + "\n" + staggered_css + "\n" + content[pos:]
                with open(p, "w", encoding="utf-8") as f:
                    f.write(content)
                print(f"Added one-after-another staggered animations to {p}!")
