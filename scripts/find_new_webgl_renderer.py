with open("assets/main-BYq3OzcY.js", "r", encoding="utf-8", errors="ignore") as f:
    text = f.read()

import re
matches = [m.start() for m in re.finditer(r'new\s+[a-zA-Z0-9_.]*WebGLRenderer', text)]
print("new WebGLRenderer occurrences:", len(matches))
for idx in matches:
    print(text[max(0, idx-20):min(len(text), idx+150)])
