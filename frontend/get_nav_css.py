import re

with open('/Users/macbookpro/Desktop/vigyanpilot/frontend/index.html', 'r') as f:
    content = f.read()

# Extract the entire navbar CSS from index.html (the block of rules)
css_rules = [
    ".nav-brand{",
    ".nav-brand img{",
    ".nav-brand:hover img{",
    ".nav-links{",
    ".nav-links>a,.drop-trigger{",
    ".nav-links>a:hover,.drop-trigger:hover{",
    ".drop-wrap{",
    ".drop-menu{",
    ".drop-wrap:hover .drop-menu{",
    ".drop-menu a{",
    ".drop-menu a:hover{",
    ".nav-right{",
    ".nav-cta{",
    ".hamburger{",
    ".hamburger span{"
]

for rule in css_rules:
    # Match the rule precisely
    match = re.search(re.escape(rule) + r'[^}]+\}', content)
    if match:
        print(match.group(0))

