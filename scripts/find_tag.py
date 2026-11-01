import re

with open('frontend/index.html', 'r', encoding='utf-8') as f:
    text = f.read()

m = re.search(r'<div[^>]*id=["\']view-dashboard["\'][^>]*>', text)
if m:
    print('Found view-dashboard:', m.group(0), 'at pos', m.start())
else:
    print('Not found')
