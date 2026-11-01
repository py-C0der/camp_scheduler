import re

with open("iit bhubanaswar/IITBBSR (1)/IITBBSR/frontend/index.html", "r", encoding="utf-8") as f:
    text = f.read()

fetches = set(re.findall(r"fetch\(['\"`](/api/[^'\"`\?]+)", text))
print("APIs called by advanced index.html:")
for api in sorted(fetches):
    print(" ", api)
