from pathlib import Path

p = Path("frontend/index.html")
text = p.read_text(encoding="utf-8")
idx = text.find('id="view-notifications"')
print("Surrounding 300 chars before view-notifications:")
print(text[max(0, idx - 300):idx + 100])
