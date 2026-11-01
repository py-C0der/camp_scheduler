import re, subprocess

with open("frontend/index.html", "r", encoding="utf-8") as f:
    text = f.read()

# Extract script content
m = re.search(r'<script>([\s\S]*?)</script>', text)
if m:
    script_text = m.group(1)
    with open("scripts/extracted_script.js", "w", encoding="utf-8") as sf:
        sf.write(script_text)
    print("Wrote extracted_script.js (length:", len(script_text), ")")

    res = subprocess.run(["node", "--check", "scripts/extracted_script.js"], capture_output=True, text=True)
    print("Returncode:", res.returncode)
    print("STDOUT:", res.stdout)
    print("STDERR:", res.stderr)
