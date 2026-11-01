import re

with open("iit bhubanaswar/CIT_CAMPscheduler_Complete_Project/landing-page/index.html", "r", encoding="utf-8") as f:
    text = f.read()

for m in re.finditer(r'(?:src|href)="([^"]+)"', text):
    url = m.group(1)
    if not url.startswith("http") and not url.startswith("//") and not url.startswith("#"):
        print("Asset link:", url)
