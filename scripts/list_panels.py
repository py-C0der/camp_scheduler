with open("frontend/index.html", "r", encoding="utf-8") as f:
    text = f.read()

import re
matches = re.findall(r'<div[^>]+class="[^"]*view-panel[^"]*"[^>]*>', text)
for m in matches:
    print(m)
