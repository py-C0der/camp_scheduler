import re

for path in ['frontend/index.html', 'public/index.html']:
    with open(path, 'r', encoding='utf-8') as f:
        text = f.read()

    # Match the <li> containing openAuthGateModal()
    pattern = re.compile(r'\s*<li>\s*<a class="nav-item" onclick="openAuthGateModal\(\)">.*?Login &amp; Role Switch.*?</a>\s*</li>', re.DOTALL)
    if pattern.search(text):
        new_text = pattern.sub('', text)
        with open(path, 'w', encoding='utf-8') as f:
            f.write(new_text)
        print(f"Removed from {path}")
    else:
        print(f"Not found in {path}")
