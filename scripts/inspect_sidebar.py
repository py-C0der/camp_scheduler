with open("frontend/index.html", "r", encoding="utf-8") as f:
    text = f.read()

pos = text.find("sidebar")
print("Position:", pos)
if pos != -1:
    print("--- SIDEBAR HTML ---")
    print(text[pos:pos+2000])

nav_pos = text.find("switchView")
print("switchView position:", nav_pos)
if nav_pos != -1:
    print("--- switchView JS ---")
    print(text[nav_pos-100:nav_pos+1000])
