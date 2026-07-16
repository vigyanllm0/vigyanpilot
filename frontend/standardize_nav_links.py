import glob
import re

files = glob.glob("/Users/macbookpro/Desktop/vigyanpilot/frontend/**/*.html", recursive=True)

count = 0
for f in files:
    with open(f, "r", encoding='utf-8') as file:
        content = file.read()

    modified = False

    if ".nav-links{" in content:
        new_content = re.sub(r'\.nav-links\{[^}]+\}', '.nav-links{display:flex;gap:32px;align-items:center;margin-left:40px}', content)
        if new_content != content:
            content = new_content
            modified = True
            
    if modified:
        with open(f, "w", encoding='utf-8') as file:
            file.write(content)
        count += 1

print(f"Fixed {count} files.")
