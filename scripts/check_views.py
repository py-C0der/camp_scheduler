import re

with open('frontend/index.html', 'r', encoding='utf-8') as f:
    text = f.read()

matches = re.findall(r'id=["\'](view-[^"\']+)["\']', text)
print("Found view elements in index.html:", matches)

all_panels = re.findall(r'class=["\'][^"\']*view-panel[^"\']*["\']', text)
print("view-panel count:", len(all_panels))

# Check CSS for .view-panel
with open('frontend/css/main.css', 'r', encoding='utf-8') as f:
    css = f.read()

print(".view-panel in CSS:", ".view-panel" in css)
if ".view-panel" in css:
    for m in re.finditer(r'\.view-panel[^{]*\{([^}]+)\}', css):
        print("CSS rule:", m.group(0))
