#!/usr/bin/env python3
"""
Bulk redesign script: applies new premium B2B SaaS theme
(Plus Jakarta Sans + Inter, deep navy nav, 4-col footer)
to ALL HTML pages across the site.

Run: python3 scripts/redesign.py
"""

import os, re, glob

FRONTEND = os.path.join(os.path.dirname(__file__), '..', 'frontend')

# ---- New shared CSS injection (will be inserted after preconnect links) ----
NEW_FONT_LINK = '''<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&amp;family=Plus+Jakarta+Sans:wght@400;500;600;700;800&amp;display=swap" rel="stylesheet">'''

NEW_ROOT_CSS = ''':root {
  --navy: #0F172A;
  --navy-light: #1E293B;
  --white: #FFFFFF;
  --slate: #F8FAFC;
  --slate-border: #E2E8F0;
  --text: #0F172A;
  --text2: #475569;
  --muted: #94A3B8;
  --primary: #2563EB;
  --bio: #059669;
  --amber: #D97706;
  --accent: #22D3EE;
  --font-h: 'Plus Jakarta Sans', sans-serif;
  --font-b: 'Inter', sans-serif;
  --max-w: 1100px;
  --sec-p: 100px;
}'''

NEW_NAV = '''  <nav>
    <div class="nav-inner" style="display:flex;justify-content:space-between;align-items:center;height:100%;max-width:1200px;margin:0 auto;padding:0 24px">
      <a href="index.html" class="nav-brand" style="display:flex;align-items:center;gap:10px;color:#fff;font-family:var(--font-h);font-size:20px;font-weight:700;text-decoration:none">
        <img src="logo.svg" alt="VigyanLLM Logo" style="width:32px;height:32px;border-radius:4px">
        <span>VigyanLLM</span>
      </a>
      <div class="nav-links" style="display:flex;gap:32px;align-items:center">
        <a href="index.html" style="font-family:var(--font-b);font-size:13px;color:#CBD5E1;font-weight:500;letter-spacing:0.02em">Home</a>
        <a href="primer.html" style="font-family:var(--font-b);font-size:13px;color:#22D3EE;font-weight:600;letter-spacing:0.02em">VPrime 1.0 \u2197</a>
        <a href="blog/index.html" style="font-family:var(--font-b);font-size:13px;color:#CBD5E1;font-weight:500;letter-spacing:0.02em">Blog</a>
        <a href="faq.html" style="font-family:var(--font-b);font-size:13px;color:#CBD5E1;font-weight:500;letter-spacing:0.02em">FAQ</a>
        <a href="about.html" style="font-family:var(--font-b);font-size:13px;color:#CBD5E1;font-weight:500;letter-spacing:0.02em">About</a>
      </div>
      <div class="nav-right" style="display:flex;align-items:center;gap:16px">
        <button class="nav-login" onclick="window.location.href='primer.html'" style="border:1.5px solid rgba(255,255,255,0.3);border-radius:4px;padding:8px 20px;font-family:var(--font-b);font-size:13px;font-weight:600;color:#fff;background:transparent;cursor:pointer">Login</button>
      </div>
    </div>
  </nav>'''

NEW_FOOTER = '''  <footer style="background:var(--navy);color:#CBD5E1;padding:80px 0 32px">
    <div style="max-width:1200px;margin:0 auto;padding:0 24px">
      <div style="display:grid;grid-template-columns:1.5fr 1fr 1fr 1fr;gap:48px;margin-bottom:60px">
        <div>
          <div style="display:flex;align-items:center;gap:10px;margin-bottom:12px">
            <img src="logo.svg" alt="VigyanLLM Logo" style="width:32px;height:32px;border-radius:4px">
            <span style="font-family:var(--font-h);font-size:20px;font-weight:700;color:#fff">VigyanLLM</span>
          </div>
          <p style="font-family:var(--font-b);font-size:13px;color:#94A3B8;margin-bottom:20px;line-height:1.6">Sovereign Healthcare &amp; Life Sciences AI.<br>Built in India. For the world.</p>
          <a href="mailto:contact@vigyanllm.in" style="font-family:var(--font-b);font-size:13px;color:var(--accent);display:block;margin-bottom:6px">contact@vigyanllm.in</a>
          <div style="display:flex;gap:12px;margin-top:24px">
            <a href="#" aria-label="Facebook" style="display:flex;align-items:center;justify-content:center;width:36px;height:36px;border-radius:8px;border:1px solid rgba(255,255,255,0.15);color:#94A3B8;text-decoration:none"><svg viewBox="0 0 24 24" style="width:18px;height:18px;fill:currentColor"><path d="M18 2h-3a5 5 0 0 0-5 5v3H7v4h3v8h4v-8h3l1-4h-4V7a1 1 0 0 1 1-1h3z"/></svg></a>
            <a href="#" aria-label="X" style="display:flex;align-items:center;justify-content:center;width:36px;height:36px;border-radius:8px;border:1px solid rgba(255,255,255,0.15);color:#94A3B8;text-decoration:none"><svg viewBox="0 0 24 24" style="width:18px;height:18px;fill:currentColor"><path d="M4 4l6.5 8.5L4 20h2l5.5-7 4.5 7h5l-7-9.5L20 4h-2l-5 6.5L9 4H4zm3 1.5h3l10 13h-3L7 5.5z"/></svg></a>
            <a href="#" aria-label="YouTube" style="display:flex;align-items:center;justify-content:center;width:36px;height:36px;border-radius:8px;border:1px solid rgba(255,255,255,0.15);color:#94A3B8;text-decoration:none"><svg viewBox="0 0 24 24" style="width:18px;height:18px;fill:currentColor"><path d="M23.5 6.2a3 3 0 0 0-2.1-2.1C19.5 3.5 12 3.5 12 3.5s-7.5 0-9.4.6a3 3 0 0 0-2.1 2.1C0 8.1 0 12 0 12s0 3.9.5 5.8a3 3 0 0 0 2.1 2.1c1.9.6 9.4.6 9.4.6s7.5 0 9.4-.6a3 3 0 0 0 2.1-2.1c.5-1.9.5-5.8.5-5.8s0-3.9-.5-5.8zM9.5 15.5V8.5l6.3 3.5-6.3 3.5z"/></svg></a>
            <a href="#" aria-label="Instagram" style="display:flex;align-items:center;justify-content:center;width:36px;height:36px;border-radius:8px;border:1px solid rgba(255,255,255,0.15);color:#94A3B8;text-decoration:none"><svg viewBox="0 0 24 24" style="width:18px;height:18px;fill:currentColor"><rect x="2" y="2" width="20" height="20" rx="5" ry="5"/><path d="M16 11.37A4 4 0 1 1 12.63 8 4 4 0 0 1 16 11.37z"/><line x1="17.5" y1="6.5" x2="17.51" y2="6.5"/></svg></a>
          </div>
        </div>
        <div>
          <h5 style="font-family:var(--font-h);font-size:12px;text-transform:uppercase;letter-spacing:0.1em;color:#fff;margin-bottom:24px;font-weight:700">Platform</h5>
          <a href="index.html#problem" style="display:block;font-family:var(--font-b);font-size:13px;color:#94A3B8;margin-bottom:14px">Problem</a>
          <a href="index.html#platform" style="display:block;font-family:var(--font-b);font-size:13px;color:#94A3B8;margin-bottom:14px">Platform</a>
          <a href="index.html#architecture" style="display:block;font-family:var(--font-b);font-size:13px;color:#94A3B8;margin-bottom:14px">Architecture</a>
          <a href="demo.html" style="display:block;font-family:var(--font-b);font-size:13px;color:#94A3B8;margin-bottom:14px">Demo</a>
        </div>
        <div>
          <h5 style="font-family:var(--font-h);font-size:12px;text-transform:uppercase;letter-spacing:0.1em;color:#fff;margin-bottom:24px;font-weight:700">Resources</h5>
          <a href="primer.html" style="display:block;font-family:var(--font-b);font-size:13px;color:#94A3B8;margin-bottom:14px">VPrime 1.0</a>
          <a href="blog/index.html" style="display:block;font-family:var(--font-b);font-size:13px;color:#94A3B8;margin-bottom:14px">Blog</a>
          <a href="faq.html" style="display:block;font-family:var(--font-b);font-size:13px;color:#94A3B8;margin-bottom:14px">FAQ</a>
          <a href="about.html" style="display:block;font-family:var(--font-b);font-size:13px;color:#94A3B8;margin-bottom:14px">About</a>
        </div>
        <div>
          <h5 style="font-family:var(--font-h);font-size:12px;text-transform:uppercase;letter-spacing:0.1em;color:#fff;margin-bottom:24px;font-weight:700">Contact</h5>
          <a href="mailto:contact@vigyanllm.in" style="display:block;font-family:var(--font-b);font-size:13px;color:#94A3B8;margin-bottom:14px">contact@vigyanllm.in</a>
          <a href="privacy.html" style="display:block;font-family:var(--font-b);font-size:13px;color:#94A3B8;margin-bottom:14px">Privacy</a>
          <a href="terms.html" style="display:block;font-family:var(--font-b);font-size:13px;color:#94A3B8;margin-bottom:14px">Terms</a>
          <a href="refund.html" style="display:block;font-family:var(--font-b);font-size:13px;color:#94A3B8;margin-bottom:14px">Refund</a>
        </div>
      </div>
      <div style="border-top:1px solid rgba(255,255,255,0.1);padding-top:24px;display:flex;justify-content:space-between;font-family:var(--font-b);font-size:12px;color:#64748B">
        <span>&copy; <script>document.write(new Date().getFullYear())</script> VigyanLLM Pvt. Ltd. \u00b7 Sovereign Research AI</span>
        <span>WWW.VIGYANLLM.IN</span>
      </div>
    </div>
  </footer>'''

# ---- Exact nav/footer strings for Group C (hub, landing-pages) ----
OLD_NAV_HUB = '''  <nav>
    <span class="brand">VigyanLLM</span>
    <div>
      <a href="https://vigyanllm.in/">Home</a>
      <a href="https://vigyanllm.in/primer.html">Primer Design</a>
      <a href="https://vigyanllm.in/demo.html">Demo</a>
      <a href="https://vigyanllm.in/about.html">About</a>
    </div>
  </nav>'''

NEW_NAV_HUB = '''  <nav style="background:#0F172A;padding:0 24px;height:64px;display:flex;align-items:center;justify-content:space-between;position:sticky;top:0;z-index:100;border-bottom:1px solid rgba(255,255,255,0.08)">
    <a href="https://vigyanllm.in/" style="color:#fff;font-family:'Plus Jakarta Sans',sans-serif;font-size:20px;font-weight:700;text-decoration:none;display:flex;align-items:center;gap:10px">
      <img src="https://vigyanllm.in/logo.svg" alt="VigyanLLM" style="width:28px;height:28px;border-radius:4px">
      VigyanLLM
    </a>
    <div style="display:flex;gap:24px;align-items:center">
      <a href="https://vigyanllm.in/" style="color:#CBD5E1;font-family:Inter,sans-serif;font-size:13px;font-weight:500;text-decoration:none">Home</a>
      <a href="https://vigyanllm.in/primer.html" style="color:#22D3EE;font-family:Inter,sans-serif;font-size:13px;font-weight:600;text-decoration:none">Primer Design</a>
      <a href="https://vigyanllm.in/demo.html" style="color:#CBD5E1;font-family:Inter,sans-serif;font-size:13px;font-weight:500;text-decoration:none">Demo</a>
      <a href="https://vigyanllm.in/about.html" style="color:#CBD5E1;font-family:Inter,sans-serif;font-size:13px;font-weight:500;text-decoration:none">About</a>
    </div>
  </nav>'''

OLD_FOOTER_HUB = '''  <footer>
    <p>VigyanLLM &copy; 2026 &mdash; Sovereign Biomedical AI Platform</p>
  </footer>'''

NEW_FOOTER_HUB = '''  <footer style="background:#0F172A;color:#CBD5E1;padding:48px 24px 24px;text-align:center">
    <div style="max-width:1200px;margin:0 auto">
      <div style="display:flex;justify-content:center;gap:24px;margin-bottom:16px;flex-wrap:wrap">
        <a href="https://vigyanllm.in/" style="color:#94A3B8;font-family:Inter,sans-serif;font-size:13px;text-decoration:none">Home</a>
        <a href="https://vigyanllm.in/primer.html" style="color:#94A3B8;font-family:Inter,sans-serif;font-size:13px;text-decoration:none">Primer Design</a>
        <a href="https://vigyanllm.in/demo.html" style="color:#94A3B8;font-family:Inter,sans-serif;font-size:13px;text-decoration:none">Demo</a>
        <a href="https://vigyanllm.in/about.html" style="color:#94A3B8;font-family:Inter,sans-serif;font-size:13px;text-decoration:none">About</a>
        <a href="https://vigyanllm.in/blog/index.html" style="color:#94A3B8;font-family:Inter,sans-serif;font-size:13px;text-decoration:none">Blog</a>
        <a href="https://vigyanllm.in/faq.html" style="color:#94A3B8;font-family:Inter,sans-serif;font-size:13px;text-decoration:none">FAQ</a>
        <a href="mailto:contact@vigyanllm.in" style="color:#22D3EE;font-family:Inter,sans-serif;font-size:13px;text-decoration:none">contact@vigyanllm.in</a>
      </div>
      <p style="font-family:Inter,sans-serif;font-size:12px;color:#64748B;border-top:1px solid rgba(255,255,255,0.1);padding-top:16px">VigyanLLM &copy; 2026 &mdash; Sovereign Biomedical AI Platform</p>
    </div>
  </footer>'''


def fix_font_link(content):
    """Replace DM Sans font link with Plus Jakarta Sans + Inter"""
    old = r'<link href="https://fonts\.googleapis\.com/css2\?family=DM\+Sans[^"]*" rel="stylesheet">'
    new = NEW_FONT_LINK
    return re.sub(old, new, content)


def fix_font_family(content):
    """Replace font-family references"""
    content = content.replace('var(--font-s)', "var(--font-b)")
    content = re.sub(r"'DM Sans'(,\s*)sans-serif", r"Inter\1sans-serif", content)
    content = content.replace("DM Sans, sans-serif", "Inter, sans-serif")
    content = content.replace("DM Sans,sans-serif", "Inter,sans-serif")
    content = content.replace("'DM Sans'", "Inter")
    content = content.replace("--font-stack:", "--font-stack_old:")
    return content


def fix_root_css(content):
    """Replace :root CSS variables with new design system"""
    # Match :root { ... } block
    root_pattern = r':root\s*\{[^}]+\}'
    
    def replace_root(match):
        block = match.group(0)
        # Check if it uses the old DM Sans variables
        if '--font-s' in block or '--bg:' in block or '--surface:' in block:
            return ':root ' + NEW_ROOT_CSS
        return block
    
    return re.sub(root_pattern, replace_root, content, count=1)


def fix_nav_css(content):
    """Add/modify nav CSS for new dark navy theme"""
    # This is handled by replacing the :root block and font links
    # and the nav HTML directly
    return content


def process_group_b(filepath):
    """Process Group B files (about, faq, blog/index, etc.) - inline-style nav/footer"""
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
    
    original = content
    
    content = fix_font_link(content)
    content = fix_root_css(content)
    content = fix_font_family(content)
    
    # Inject :root if missing after fix
    if ':root' not in content and '</style>' in content:
        content = content.replace('</style>', f'{NEW_ROOT_CSS}\n</style>', 1)
    
    # Inject font link if missing
    if 'fonts.googleapis.com' not in content:
        content = content.replace('</head>', f'  {NEW_FONT_LINK}\n</head>', 1)
    
    # Replace nav if present
    old_nav_pattern = r'<nav>[\s\S]*?<div class="nav-inner"[^>]*>[\s\S]*?</nav>'
    if re.search(old_nav_pattern, content):
        content = re.sub(old_nav_pattern, NEW_NAV, content, count=1)
    
    # Replace footer if present
    if '<footer' in content:
        content = re.sub(r'<footer[^>]*>[\s\S]*?</footer>', NEW_FOOTER, content, count=1)
    
    if content != original:
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)
        return True
    return False


def process_group_c(filepath):
    """Process Group C files (hub, landing-pages) - shared nav/footer"""
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
    
    original = content
    
    # 1. Fix font link
    # These pages might not have a font link - add one if missing
    if 'fonts.googleapis.com' not in content:
        # Add font link before </head>
        content = content.replace('</head>', f'  {NEW_FONT_LINK}\n</head>')
    else:
        content = fix_font_link(content)
    
    # 2. Replace nav
    if OLD_NAV_HUB in content:
        content = content.replace(OLD_NAV_HUB, NEW_NAV_HUB)
    
    # 3. Replace footer
    if OLD_FOOTER_HUB in content:
        content = content.replace(OLD_FOOTER_HUB, NEW_FOOTER_HUB)
    
    # 4. Fix font-family in CSS
    content = fix_font_family(content)
    
    if content != original:
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)
        return True
    return False


def process_glossary(filepath):
    """Process glossary pages - different nav structure"""
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
    
    original = content
    
    # 1. Fix font link
    if 'fonts.googleapis.com' not in content:
        content = content.replace('</head>', f'  {NEW_FONT_LINK}\n</head>')
    else:
        content = fix_font_link(content)
    
    # 2. Fix font-family in CSS
    content = fix_font_family(content)
    
    # 3. Replace nav (glossary-specific)
    old_nav_pattern = r'<nav class="nav"[\s\S]*?</nav>'
    new_nav = '''  <nav style="background:#0F172A;padding:0.75rem 1.5rem;display:flex;align-items:center;justify-content:space-between;position:sticky;top:0;z-index:100;border-bottom:1px solid rgba(255,255,255,0.08)">
    <a href="../index.html" style="color:#fff;font-family:\\'Plus Jakarta Sans\\',sans-serif;font-size:1.1rem;font-weight:700;text-decoration:none">VigyanLLM</a>
    <ul style="display:flex;gap:1.25rem;align-items:center;list-style:none;margin:0">
      <li><a href="../glossary-index.html" style="color:#CBD5E1;font-family:Inter,sans-serif;font-size:0.875rem;text-decoration:none">Glossary</a></li>
      <li><a href="../index.html" style="color:#22D3EE;font-family:Inter,sans-serif;font-size:0.875rem;text-decoration:none">Back to VigyanLLM \u2192</a></li>
    </ul>
  </nav>'''
    content = re.sub(old_nav_pattern, new_nav, content, count=1)
    
    # 4. Replace footer
    old_footer_pattern = r'<footer>[\s\S]*?</footer>'
    new_footer = '''  <footer style="background:#0F172A;color:#CBD5E1;padding:32px 24px;text-align:center;margin-top:3rem">
    <p style="font-family:Inter,sans-serif;font-size:0.85rem;color:#64748B">&copy; 2026 VigyanLLM &mdash; Biomedical AI Platform. <a href="../index.html" style="color:#22D3EE">vigyanllm.in</a></p>
  </footer>'''
    content = re.sub(old_footer_pattern, new_footer, content, count=1)
    
    # 5. Replace :root CSS block
    content = fix_root_css(content)
    
    if content != original:
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)
        return True
    return False


def process_gene_prefers(filepath):
    """Process gene-prefers pages"""
    # Same as glossary pattern
    return process_glossary(filepath)


def process_blog_article(filepath):
    """Process blog article pages"""
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
    
    original = content
    
    # Check if it has the Group B nav pattern
    if '<nav>' in content and 'nav-inner' in content:
        return process_group_b(filepath)
    
    # Otherwise treat as hub-like
    if 'fonts.googleapis.com' not in content:
        content = content.replace('</head>', f'  {NEW_FONT_LINK}\n</head>')
    else:
        content = fix_font_link(content)
    
    content = fix_font_family(content)
    
    # Replace rough nav/footer patterns
    old_nav = re.search(r'<nav>[\s\S]*?</nav>', content)
    old_footer = re.search(r'<footer[^>]*>[\s\S]*?</footer>', content)
    
    if old_nav:
        content = content.replace(old_nav.group(0), NEW_NAV_HUB, 1)
    if old_footer:
        content = content.replace(old_footer.group(0), NEW_FOOTER_HUB, 1)
    
    if content != original:
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)
        return True
    return False


def main():
    total = 0
    changed = 0
    errors = []
    
    # Collect all HTML files
    html_files = []
    for root, dirs, files in os.walk(FRONTEND):
        # Skip qa_runs directory
        if 'qa_runs' in root:
            continue
        # Skip api directory
        if '/api/' in root or root.endswith('/api'):
            continue
        for f in files:
            if f.endswith('.html'):
                html_files.append(os.path.join(root, f))
    
    print(f"Found {len(html_files)} HTML files to process")
    
    for filepath in sorted(html_files):
        relpath = os.path.relpath(filepath, FRONTEND)
        total += 1
        
        try:
            # Determine file group
            if 'hub/' in relpath or 'landing-pages/' in relpath:
                ok = process_group_c(filepath)
            elif 'glossary/' in relpath:
                ok = process_glossary(filepath)
            elif 'gene-prefers/' in relpath:
                ok = process_gene_prefers(filepath)
            elif 'blog/' in relpath and relpath != 'blog/index.html':
                ok = process_blog_article(filepath)
            elif os.path.basename(filepath) == 'index.html':
                # Skip index.html (already redesigned)
                ok = False
            else:
                # Treat as Group B
                ok = process_group_b(filepath)
            
            if ok:
                changed += 1
                print(f"  UPDATED: {relpath}")
        except Exception as e:
            errors.append((relpath, str(e)))
            print(f"  ERROR: {relpath}: {e}")
    
    print(f"\nDone: {changed} files changed, {total - changed - len(errors)} unchanged, {len(errors)} errors")
    if errors:
        print("\nErrors:")
        for path, err in errors:
            print(f"  {path}: {err}")


if __name__ == '__main__':
    main()
