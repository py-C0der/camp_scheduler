import re
from pathlib import Path

# Clean all html files across entire repository
for p in Path('.').glob('**/*.html'):
    if 'node_modules' in str(p) or '.git' in str(p):
        continue
    content = p.read_text(encoding='utf-8', errors='ignore')
    modified = False
    
    # 1. Remove duplicate }); in script
    duplicate_bracket = re.compile(r'\}\);\s*\}\);\s*let dashboardData', re.MULTILINE)
    if duplicate_bracket.search(content):
        content = duplicate_bracket.sub('});\n  let dashboardData', content)
        modified = True
        print(f"Fixed duplicate bracket in {p}")
        
    # 2. Remove all nav-badge elements from HTML (regardless of attributes)
    badge_pattern = re.compile(r'<span[^>]*class="[^"]*nav-badge[^"]*"[^>]*>[^<]*</span>', re.IGNORECASE)
    if badge_pattern.search(content):
        content = badge_pattern.sub('', content)
        modified = True
        print(f"Removed nav-badge spans in {p}")
        
    # 3. Ensure .nav-badge is hidden in CSS
    if '.nav-badge {' in content and 'display: none !important' not in content:
        content = content.replace('.nav-badge {', '.nav-badge { display: none !important; ')
        modified = True
        print(f"Added display:none to .nav-badge in {p}")
        
    if modified:
        p.write_text(content, encoding='utf-8')

print("All HTML files cleaned successfully!")
