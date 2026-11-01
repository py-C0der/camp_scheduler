import glob, os, re

for root, dirs, files in os.walk('iit bhubanaswar'):
    for f in files:
        if f.endswith(('.html', '.css')):
            p = os.path.join(root, f)
            try:
                with open(p, 'r', encoding='utf-8', errors='ignore') as fh:
                    txt = fh.read()
                    kf = re.findall(r'@keyframes\s+([a-zA-Z0-9_-]+)', txt)
                    if kf:
                        print(f"{p} has keyframes:", kf[:8])
            except Exception:
                pass
