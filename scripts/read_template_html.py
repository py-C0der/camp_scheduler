with open(r"iit bhubanaswar\CHRONOGRID_IITBBSR-main\CHRONOGRID_IITBBSR-main\template.html", "r", encoding="utf-8") as f:
    text = f.read()

print("Length of template.html:", len(text))
for line in text.splitlines()[:40]:
    print(line)
