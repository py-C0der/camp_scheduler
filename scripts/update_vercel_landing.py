with open("vercel.json", "r", encoding="utf-8") as f:
    text = f.read()

text = text.replace('"destination": "/public/planner.html"', '"destination": "/public/intro.html"')

with open("vercel.json", "w", encoding="utf-8") as f:
    f.write(text)
print("Updated vercel.json root destination to intro.html!")
