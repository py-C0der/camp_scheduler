with open("frontend/index.html", "r", encoding="utf-8") as f:
    text = f.read()

import re
matches = re.findall(r'<aside.*?>[\s\S]*?</aside>', text)
if matches:
    print("--- ASIDE ELEMENT ---")
    print(matches[0].encode('ascii', errors='replace').decode('ascii'))
