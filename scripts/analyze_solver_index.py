with open(r"iit bhubanaswar\CIT_CAMPscheduler_Complete_Project\campscheduler-solver\index.html", "r", encoding="utf-8") as f:
    text = f.read()

import re
sections = re.findall(r'<section[^>]*>[\s\S]*?</section>', text)
print(f"Total sections: {len(sections)}")
for i, s in enumerate(sections):
    title_m = re.search(r'<h[1-4][^>]*>(.*?)</h[1-4]>', s)
    t = title_m.group(1) if title_m else "No heading"
    print(f"Section {i+1}: {t[:80]}")

# Look at 3D WebGL scripts in this file
webgl_script = re.findall(r'<script.*?>([\s\S]*?)</script>', text)
print(f"\nTotal scripts: {len(webgl_script)}")
for i, sc in enumerate(webgl_script):
    if 'THREE' in sc or 'scene' in sc or 'animate' in sc:
        print(f"Script {i+1} has 3D Three.js code! Length: {len(sc)}")
        for l in sc.splitlines()[:25]:
            print("  ", l)
