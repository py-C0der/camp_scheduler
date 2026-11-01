import re

with open("frontend/index.html", "r", encoding="utf-8") as f:
    lines = f.readlines()

view_starts = []
for idx, line in enumerate(lines):
    m = re.search(r'id=["\'](view-[^"\']+)["\']', line)
    if m:
        view_starts.append((idx + 1, m.group(1)))

for idx, (lineno, name) in enumerate(view_starts):
    next_lineno = view_starts[idx + 1][0] if idx + 1 < len(view_starts) else len(lines)
    print(f"{name}: lines {lineno} to {next_lineno} (span: {next_lineno - lineno} lines)")
