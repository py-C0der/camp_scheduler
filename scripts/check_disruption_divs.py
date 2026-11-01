from pathlib import Path

text = Path("frontend/index.html").read_text(encoding="utf-8")

dis_idx = text.find('id="view-disruptions"')
notif_idx = text.find('id="view-notifications"')

dis_content = text[dis_idx:notif_idx]

open_divs = dis_content.count("<div")
close_divs = dis_content.count("</div>")
diff = open_divs - close_divs

print(f"Inside view-disruptions section:")
print(f"Open divs: {open_divs}")
print(f"Close divs: {close_divs}")
print(f"Unclosed divs: {diff}")

# Show the last 400 characters before view-notifications
print("\nLast 400 characters before view-notifications:")
print(text[notif_idx - 400:notif_idx])
