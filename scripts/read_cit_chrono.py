with open(r"iit bhubanaswar\CHRONOGRID_IITBBSR-main\CHRONOGRID_IITBBSR-main\reference\cit_chronogrid_platform.html", "r", encoding="utf-8") as f:
    text = f.read()

print("Length:", len(text))
for line in text.splitlines()[:50]:
    print(line)
