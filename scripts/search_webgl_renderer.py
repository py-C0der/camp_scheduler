with open("assets/main-BYq3OzcY.js", "r", encoding="utf-8", errors="ignore") as f:
    text = f.read()

import re
matches = [m.start() for m in re.finditer(r'WebGLRenderer|powerPreference|getContext|hardware', text, re.IGNORECASE)]
print("Total WebGL renderer matches:", len(matches))
for idx in matches[:10]:
    print(text[max(0, idx-60):min(len(text), idx+100)])
