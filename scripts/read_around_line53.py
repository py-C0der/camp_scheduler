with open("scripts/extracted_script.js", "r", encoding="utf-8") as f:
    lines = f.readlines()

for i in range(max(0, 30), min(len(lines), 70)):
    print(f"{i+1}: {lines[i]}", end="")
