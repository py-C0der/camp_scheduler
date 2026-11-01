from pathlib import Path

text = Path("frontend/index.html").read_text(encoding="utf-8")

views = [
    ('view-dashboard', 'view-timetable'),
    ('view-timetable', 'view-validations'),
    ('view-validations', 'view-examinations'),
    ('view-examinations', 'view-bookings'),
    ('view-bookings', 'view-disruptions'),
    ('view-disruptions', 'view-notifications'),
    ('view-notifications', 'view-ai-assistant'),
]

for v1, v2 in views:
    idx1 = text.find(f'id="{v1}"')
    idx2 = text.find(f'id="{v2}"')
    chunk = text[idx1:idx2]
    open_c = chunk.count("<div")
    close_c = chunk.count("</div>")
    print(f"{v1} -> {v2}: open={open_c}, close={close_c}, diff={open_c - close_c}")

# Check from view-ai-assistant to the end of main content
idx_ai = text.find('id="view-ai-assistant"')
idx_end = text.find('</main>')
chunk = text[idx_ai:idx_end]
open_c = chunk.count("<div")
close_c = chunk.count("</div>")
print(f"view-ai-assistant -> </main>: open={open_c}, close={close_c}, diff={open_c - close_c}")
