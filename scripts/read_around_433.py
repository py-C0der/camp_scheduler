with open('backend/main.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()

print("Total lines in backend/main.py:", len(lines))
for i in range(430, min(445, len(lines))):
    print(f"L{i+1}: {repr(lines[i][:60])}")
