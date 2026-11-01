with open("frontend/index.html", "r", encoding="utf-8") as f:
    text = f.read()

pos = text.find("function switchNav")
print(text[pos+2000:pos+4000])
