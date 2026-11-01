with open("public/dashboard.html", "r", encoding="utf-8") as f:
    text = f.read()

import re
matches = re.findall(r'<aside.*?>[\s\S]*?</aside>', text)
if matches:
    print("--- ASIDE IN dashboard.html ---")
    print(matches[0][:1500].encode('ascii', errors='replace').decode('ascii'))
