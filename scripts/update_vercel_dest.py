from pathlib import Path

p = Path("vercel.json")
text = p.read_text(encoding="utf-8")
text = text.replace('"/public/intro.html"', '"/public/index.html"')
p.write_text(text, encoding="utf-8")
print("Updated vercel.json root to /public/index.html!")
