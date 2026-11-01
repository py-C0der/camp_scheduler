with open("iit bhubanaswar/CIT_CAMPscheduler_Complete_Project/landing-page/index.html", "r", encoding="utf-8") as f:
    text = f.read()

import re
scripts = re.findall(r'<script.*?>[\s\S]*?</script>', text)
print("Scripts in landing-page index.html:", len(scripts))
for s in scripts:
    print(s[:200])

canvas = re.findall(r'<canvas.*?>', text)
print("Canvas in landing-page index.html:", canvas)
