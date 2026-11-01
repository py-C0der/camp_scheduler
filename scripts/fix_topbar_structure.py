import re

for path in ['frontend/index.html', 'public/index.html']:
    with open(path, 'r', encoding='utf-8') as f:
        text = f.read()

    # Pattern to find the user-avatar-wrapper and following stray tags up to </header>
    pattern = re.compile(
        r'(<div class="user-avatar-wrapper">.*?</div>\s*)\s*<span style="font-size:\s*0\.75rem;\s*color:\s*var\(--ink-secondary\);">&#9662;</span>\s*</div>\s*</div>\s*</header>',
        re.DOTALL
    )

    if pattern.search(text):
        new_text = pattern.sub(r'\1</div>\n  </header>', text)
        with open(path, 'w', encoding='utf-8') as f:
            f.write(new_text)
        print(f"Successfully fixed topbar closing tags in {path}")
    else:
        print(f"Pattern did not match in {path}")
