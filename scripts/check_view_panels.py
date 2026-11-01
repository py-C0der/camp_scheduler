with open("frontend/index.html", "r", encoding="utf-8") as f:
    text = f.read()

import re
view_ids = ['view-dashboard', 'view-timetable', 'view-validations', 'view-examinations', 'view-bookings', 'view-disruptions', 'view-notifications', 'view-ai']
for vid in view_ids:
    m = re.search(rf'<[^>]+id="{vid}"[^>]*>', text)
    if m:
        print(f"Found {vid}: {m.group(0)}")
    else:
        print(f"MISSING {vid}")

print("Total elements with class view-panel:", len(re.findall(r'class="[^"]*view-panel[^"]*"', text)))
