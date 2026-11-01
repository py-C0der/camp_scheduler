from pathlib import Path
import re

page_defs = [
    ("dashboard", "Dashboard", "/dashboard", "&#9632;"),
    ("timetable", "Timetable", "/timetable", "&#9776;"),
    ("validations", "Validations Audit", "/validations", "&#10004;"),
    ("examinations", "Examinations", "/examinations", "&#128197;"),
    ("bookings", "Smart Venue Bookings", "/bookings", "&#127970;"),
    ("disruptions", "Disruptions", "/disruptions", "&#9888;"),
    ("notifications", "Notifications", "/notifications", "&#128276;"),
    ("ai-assistant", "AI Assistant", "/ai-assistant", "&#10024;")
]

# 1. Fix standalone HTML pages (dashboard.html, timetable.html, etc.)
for base_dir in [Path("frontend"), Path("public")]:
    for p_name, title, url, icon in page_defs:
        fpath = base_dir / f"{p_name}.html"
        if not fpath.exists():
            continue
        with open(fpath, "r", encoding="utf-8") as f:
            content = f.read()

        # Replace any onclick with return false
        for target_p, target_title, target_url, target_icon in page_defs:
            # Pattern like href="timetable.html" onclick="if(window.switchNav)..."
            pattern1 = rf'href="{target_p}\.html"\s+onclick="[^"]*"'
            replacement1 = f'href="{target_url}"'
            content = re.sub(pattern1, replacement1, content)

            pattern2 = rf'href="{target_url}"\s+onclick="[^"]*"'
            content = re.sub(pattern2, replacement1, content)

        with open(fpath, "w", encoding="utf-8") as f:
            f.write(content)
        print(f"Fixed sidebar links in {fpath}")

# 2. In index.html, ensure switchNav supports both onclick and URL hash/path
with open("frontend/index.html", "r", encoding="utf-8") as f:
    idx_content = f.read()

# Make sure switchNav updates the active view and URL hash
nav_patch = """
  function switchNav(viewName) {
    document.querySelectorAll('.view-panel').forEach(el => el.classList.remove('active'));
    document.querySelectorAll('.sidebar .nav-item').forEach(el => el.classList.remove('active'));

    try {
      window.scrollTo({ top: 0, behavior: 'smooth' });
    } catch(e) {}

    const viewMap = {
      'dashboard': { panel: 'view-dashboard', btn: 'navItemDashboard', title: 'Campus Operations Dashboard' },
      'timetable': { panel: 'view-timetable', btn: 'navItemTimetable', title: 'Academic Timetable Management', onOpen: () => typeof renderTimetableGrid === 'function' && renderTimetableGrid() },
      'validations': { panel: 'view-validations', btn: 'navItemValidations', title: 'System Constraints & Validation Audit', onOpen: () => typeof loadValidationsAudit === 'function' && loadValidationsAudit() },
      'dataset': { panel: 'view-validations', btn: 'navItemDataset', title: 'System Constraints & Validation Audit', onOpen: () => typeof loadValidationsAudit === 'function' && loadValidationsAudit() },
      'disruptions': { panel: 'view-disruptions', btn: 'navItemDisruptions', title: 'Disruption Management & Rescheduling Engine', onOpen: () => typeof loadDisruptionModule === 'function' && loadDisruptionModule() },
      'bookings': { panel: 'view-bookings', btn: 'navItemBookings', title: 'Smart Venue Booking & Approval Management', onOpen: () => typeof loadBookingModule === 'function' && loadBookingModule() },
      'examinations': { panel: 'view-examinations', btn: 'navItemExaminations', title: 'Examination Scheduling Management', onOpen: () => typeof loadExamModule === 'function' && loadExamModule() },
      'notifications': { panel: 'view-notifications', btn: 'navItemNotifications', title: 'Notification, Alerts & Communication Management', onOpen: () => typeof loadNotificationModule === 'function' && loadNotificationModule() },
      'ai-assistant': { panel: 'view-ai-assistant', btn: 'navItemAiAssistant', title: 'AI Scheduling Assistant & Decision Explainability', onOpen: () => typeof loadAiAssistantModule === 'function' && loadAiAssistantModule() }
    };

    const target = viewMap[viewName] || viewMap['dashboard'];
    const pEl = document.getElementById(target.panel);
    if (pEl) pEl.classList.add('active');

    const bEl = document.getElementById(target.btn);
    if (bEl) bEl.classList.add('active');

    const tEl = document.getElementById('pageTitle');
    if (tEl) tEl.textContent = target.title;

    if (target.onOpen) {
      try { target.onOpen(); } catch(err) { console.warn("Panel init warning:", err); }
    }
  }
  window.switchNav = switchNav;
"""

# Replace switchNav definition
pos_sn = idx_content.find("function switchNav(viewName) {")
if pos_sn != -1:
    pos_end_sn = idx_content.find("function showPlaceholder", pos_sn)
    if pos_end_sn != -1:
        idx_content = idx_content[:pos_sn] + nav_patch.strip() + "\n\n  " + idx_content[pos_end_sn:]
        print("Patched robust switchNav in index.html!")

for p in ["frontend/index.html", "public/index.html"]:
    with open(p, "w", encoding="utf-8") as f:
        f.write(idx_content)
