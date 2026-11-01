with open("frontend/src/app.ts", "r", encoding="utf-8") as f:
    lines = f.readlines()

for i, l in enumerate(lines):
    if "async function fetchDatasetInfo()" in l:
        # insert after line i + 9
        insert_idx = i + 10
        lines.insert(insert_idx, "      await fetchBaselineDataset();\n      renderCsvMatrixGrid();\n")
        break

with open("frontend/src/app.ts", "w", encoding="utf-8") as f:
    f.writelines(lines)

print("Updated fetchDatasetInfo in frontend/src/app.ts successfully")
