from pathlib import Path

for p in [Path("frontend/login.html"), Path("public/login.html")]:
    if not p.exists():
        continue
    c = p.read_text(encoding="utf-8")
    
    # Clean role cards
    c = c.replace("🏛️ Dean Academics", "🏛️ Dean")
    c = c.replace("🎓 CSE Coordinator", "📅 Coordinator")
    c = c.replace("👨‍🏫 Dr. Arvind Kumar", "👨‍🏫 Faculty")
    c = c.replace("🤖 Robotics Club", "🎟️ Clubs")
    c = c.replace("Dr. Arvind Rao", "Faculty")
    c = c.replace("Dr. Arvind Kumar", "Faculty")
    c = c.replace("Robotics Club", "Clubs")
    
    # Back to Landing -> Back to Home
    c = c.replace("&larr; Back to Landing", "&larr; Back to Workspace")
    
    p.write_text(c, encoding="utf-8")
    print(f"Cleaned role titles in {p}")

print("login.html role titles cleaned!")
