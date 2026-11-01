with open("iit bhubanaswar/CIT_CAMPscheduler_Complete_Project/landing-page/index.html", "r", encoding="utf-8") as f:
    text = f.read()

import re
matches = re.findall(r'@keyframes\s+[a-zA-Z0-9_-]+\s*\{[^}]*\}', text)
for m in matches:
    print(m)
