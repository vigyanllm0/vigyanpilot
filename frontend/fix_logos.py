import glob
import os
import re

files = glob.glob("/Users/macbookpro/Desktop/vigyanpilot/frontend/*.html")

for f in files:
    with open(f, "r") as file:
        content = file.read()
    
    modified = False
    
    # 1. Replace the CSS class .logo -> .nav-brand
    if ".logo{" in content or ".logo-img{" in content:
        # We will replace the entire block of .logo CSS with .nav-brand CSS
        content = re.sub(r'\.logo\{[^}]+\}', '.nav-brand{display:flex;align-items:center;gap:10px;color:#fff;font-family:var(--font-h);font-size:20px;font-weight:800}', content)
        content = re.sub(r'\.logo-img\{[^}]+\}', '.nav-brand img{width:34px;height:34px;border-radius:8px;transition:transform .3s}\n.nav-brand:hover img{transform:rotate(-10deg)}', content)
        content = re.sub(r'\.logo-text\{[^}]+\}', '', content)
        modified = True

    # 2. Replace the HTML class="logo" -> class="nav-brand"
    if 'class="logo"' in content:
        content = content.replace('class="logo"', 'class="nav-brand"')
        content = content.replace('class="logo-img"', '')
        content = content.replace('class="logo-text"', '')
        modified = True
        
    if modified:
        # Clean up empty lines from .logo-text removal
        content = "\n".join([line for line in content.split("\n") if line.strip() != ""])
        with open(f, "w") as file:
            file.write(content)
        print(f"Fixed {f}")
