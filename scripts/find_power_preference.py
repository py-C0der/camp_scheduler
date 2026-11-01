with open("assets/main-BYq3OzcY.js", "r", encoding="utf-8", errors="ignore") as f:
    text = f.read()

import re
matches = [m.start() for m in re.finditer(r'powerPreference|antialias', text)]
print("Total occurrences:", len(matches))
for idx in matches:
    print(text[max(0, idx-50):min(len(text), idx+150)])
