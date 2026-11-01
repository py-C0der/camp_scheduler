with open("frontend/planner.html", "r", encoding="utf-8") as f:
    text = f.read()

import re
pos = text.find("<style>")
end_pos = text.find("</style>")
if pos != -1 and end_pos != -1:
    css = text[pos:end_pos]
    keyframes = re.findall(r'@keyframes\s+([a-zA-Z0-9_-]+)', css)
    print("Keyframes in planner.html:", keyframes)

# Check cards or animation elements
cards = re.findall(r'<div[^>]*class="[^"]*(?:card|note|planner|hero)[^"]*"', text)
print("Cards/Notes count:", len(cards))
for c in cards[:10]:
    print(" ", c)
