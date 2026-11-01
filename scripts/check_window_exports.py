import re

with open("frontend/src/app.ts", "r", encoding="utf-8") as f:
    text = f.read()

# Find all lines like: (window as any).foo = foo;
assignments = re.findall(r'\(window as any\)\.(\w+)\s*=\s*(\w+);', text)

print(f"Total window assignments: {len(assignments)}")
undefined = []
for win_prop, var_name in assignments:
    # Check if var_name is declared with function or const or let or var
    pat = rf'\b(function|const|let|var)\s+{var_name}\b'
    if not re.search(pat, text):
        undefined.append((win_prop, var_name))

print("Undefined variables assigned to window:", undefined)
