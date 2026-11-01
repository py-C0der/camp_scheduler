with open("vercel.json", "r", encoding="utf-8") as f:
    text = f.read()

text = text.replace('"destination": "/public/intro.html"', '"destination": "/public/planner.html"')

with open("vercel.json", "w", encoding="utf-8") as f:
    f.write(text)
print("Updated vercel.json root destination to planner.html!")
