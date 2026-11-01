import glob, re
from pathlib import Path

files = glob.glob('frontend/**/*.html', recursive=True) + glob.glob('public/**/*.html', recursive=True)

badge_pattern = re.compile(r'\s*<span\s+class="nav-badge"[^>]*>.*?</span>', re.DOTALL)

for fpath in files:
    with open(fpath, 'r', encoding='utf-8') as f:
        content = f.read()

    new_content, count = badge_pattern.subn('', content)
    if count > 0:
        with open(fpath, 'w', encoding='utf-8') as f:
            f.write(new_content)
        print(f"Removed {count} nav-badges from {fpath}")

# Also hide .nav-badge in CSS just in case any dynamic script inserts them
css_pattern = re.compile(r'\.nav-badge\s*\{[^}]*\}')
for fpath in files:
    with open(fpath, 'r', encoding='utf-8') as f:
        content = f.read()
    if '.nav-badge' in content:
        content = content.replace('.nav-badge {', '.nav-badge { display: none !important; ')
        with open(fpath, 'w', encoding='utf-8') as f:
            f.write(content)
        print(f"Added display:none to .nav-badge in {fpath}")
