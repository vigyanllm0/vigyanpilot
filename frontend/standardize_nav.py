import glob
import re
import os

files = glob.glob("/Users/macbookpro/Desktop/vigyanpilot/frontend/**/*.html", recursive=True)

count = 0
for f in files:
    with open(f, "r", encoding='utf-8') as file:
        content = file.read()

    modified = False

    # Standardize CSS for .nav-brand
    if ".nav-brand{" in content:
        new_content = re.sub(r'\.nav-brand\{[^}]+\}', '.nav-brand{display:flex;align-items:center;gap:10px;color:#fff;font-family:var(--font-h);font-size:20px;font-weight:800}', content)
        if new_content != content:
            content = new_content
            modified = True

    if ".nav-brand img" in content:
        new_content = re.sub(r'\.nav-brand img\s*\{[^}]+\}', '.nav-brand img{width:34px;height:34px;border-radius:8px;transition:transform .3s}', content)
        if new_content != content:
            content = new_content
            modified = True

    brand_match = re.search(r'<a[^>]+class="nav-brand"[^>]*>[\s\S]*?</a>', content)
    if brand_match:
        old_brand_html = brand_match.group(0)
        
        depth = f.count('/') - "/Users/macbookpro/Desktop/vigyanpilot/frontend".count('/') - 1
        prefix = "../" * depth if depth > 0 else ""
        
        expected_html = f"""<a href="{prefix}index.html" class="nav-brand">
    <img src="{prefix}logo.svg" alt="VigyanLLM Logo" width="48" height="48" style="border-radius:8px">
    <span>VigyanLLM</span>
  </a>"""
        
        if old_brand_html.strip() != expected_html.strip():
            # If the only difference is leading whitespace, it's fine, but let's just replace it.
            content = content.replace(old_brand_html, expected_html)
            modified = True
            
    if modified:
        with open(f, "w", encoding='utf-8') as file:
            file.write(content)
        count += 1
        # print(f"Standardized {f}")

print(f"Fixed {count} files.")
