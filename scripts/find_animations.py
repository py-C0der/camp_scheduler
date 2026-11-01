import glob, os, re

for root, dirs, files in os.walk('iit bhubanaswar'):
    for f in files:
        if f.endswith(('.html', '.js', '.css', '.py')):
            p = os.path.join(root, f)
            try:
                with open(p, 'r', encoding='utf-8', errors='ignore') as fh:
                    txt = fh.read()
                    if 'one after another' in txt.lower() or 'animation' in txt.lower() or 'stage' in txt.lower() or 'origami' in txt.lower():
                        # Find occurrences of stage or animation sequence
                        matches = re.findall(r'(stage\d|stagger|keyframes|sequence|flip|carousel|steps)', txt, re.IGNORECASE)
                        if len(matches) > 10 and not 'node_modules' in p:
                            print(f"{p} -> {len(matches)} animation matches")
            except Exception:
                pass
