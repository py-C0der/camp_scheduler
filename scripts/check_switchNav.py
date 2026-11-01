with open("frontend/index.html", "r", encoding="utf-8") as f:
    text = f.read()

pos = text.find("function switchNav")
if pos == -1:
    pos = text.find("switchNav")
print("Position:", pos)
if pos != -1:
    print(text[pos:pos+1500])
else:
    print("switchNav NOT FOUND!")
