from pathlib import Path
import re

text = Path("frontend/index.html").read_text(encoding="utf-8")

views = [
    'view-dashboard',
    'view-timetable',
    'view-examinations',
    'view-bookings',
    'view-disruptions',
    'view-validations',
    'view-notifications',
    'view-ai-assistant'
]

for v in views:
    idx = text.find(f'id="{v}"')
    print(f"View {v} at index {idx}")

# Check lines between view-disruptions and view-validations
dis_idx = text.find('id="view-disruptions"')
val_idx = text.find('id="view-validations"')
print("\nBetween disruptions and validations:")
print(text[val_idx - 150:val_idx + 60])

# Check lines between validations and notifications
notif_idx = text.find('id="view-notifications"')
print("\nBetween validations and notifications:")
print(text[notif_idx - 150:notif_idx + 60])
