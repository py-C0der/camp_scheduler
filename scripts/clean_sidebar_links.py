with open("frontend/index.html", "r", encoding="utf-8") as f:
    text = f.read()

# Clean up duplicate Public Landing items in sidebar
target = '<li class="nav-item"><a href="/" style="text-decoration:none; color:inherit; display:flex; align-items:center; gap:10px; width:100%;"><span>🌐</span> <span>Public Landing ↗</span></a></li>'

# Keep only first occurrence in sidebar
pos = text.find(target)
if pos != -1:
    first_part = text[:pos + len(target)]
    rest_part = text[pos + len(target):].replace(target, '')
    text = first_part + rest_part
    print("Cleaned duplicate Public Landing links from sidebar!")

for p in ["frontend/index.html", "public/index.html"]:
    with open(p, "w", encoding="utf-8") as f:
        f.write(text)
