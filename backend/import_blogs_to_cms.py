"""
Import all existing blog posts and glossary pages into the CMS.

Usage:
  cd backend && python3 import_blogs_to_cms.py

Requires JWT_SECRET env var and the CMS server running on port 8001.
"""

import os, sys, json, re, glob, html as html_module
from datetime import datetime
import urllib.request, urllib.error

JWT_SECRET = os.environ.get("JWT_SECRET")
if not JWT_SECRET:
    print("ERROR: JWT_SECRET env var required")
    sys.exit(1)

CMS_URL = "http://localhost:8001"
AUTH_EMAIL = "contact@vigyanllm.in"
AUTH_PASSWORD = "Vigyan@hemant.9817&hs"
FRONTEND_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "frontend")

def get_token():
    data = json.dumps({"email": AUTH_EMAIL, "password": AUTH_PASSWORD}).encode()
    req = urllib.request.Request(
        f"{CMS_URL}/api/v1/cms/auth/login",
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    resp = urllib.request.urlopen(req)
    body = json.loads(resp.read())
    return body["token"]

def cms_request(method, path, body=None, token=None):
    headers = {}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    if body is not None:
        data = json.dumps(body).encode()
        headers["Content-Type"] = "application/json"
    else:
        data = None
    req = urllib.request.Request(
        f"{CMS_URL}{path}",
        data=data,
        headers=headers,
        method=method,
    )
    try:
        resp = urllib.request.urlopen(req)
        return json.loads(resp.read())
    except urllib.error.HTTPError as e:
        err = e.read().decode()
        print(f"  HTTP {e.code}: {err[:200]}")
        return None

def extract_title_from_html(content, filename):
    """Extract <title> from HTML, fallback to filename."""
    m = re.search(r'<title>(.*?)</title>', content, re.DOTALL)
    if m:
        return html_module.unescape(m.group(1)).strip()
    return filename.replace(".html", "").replace("-", " ").title()

def extract_description_from_html(content):
    """Extract meta description."""
    m = re.search(r'<meta\s+name=["\']description["\']\s+content=["\'](.*?)["\']', content, re.DOTALL)
    if m:
        return html_module.unescape(m.group(1)).strip()
    return ""

def extract_body_html(content):
    """Extract main content between <body> and </body>, stripping nav/footer."""
    m = re.search(r'<body[^>]*>(.*?)</body>', content, re.DOTALL)
    if not m:
        return ""
    body = m.group(1)
    # Remove nav, footer, scripts, styles
    body = re.sub(r'<nav[^>]*>.*?</nav>', '', body, flags=re.DOTALL)
    body = re.sub(r'<footer[^>]*>.*?</footer>', '', body, flags=re.DOTALL)
    body = re.sub(r'<script[^>]*>.*?</script>', '', body, flags=re.DOTALL)
    body = re.sub(r'<style[^>]*>.*?</style>', '', body, flags=re.DOTALL)
    body = re.sub(r'<aside[^>]*>.*?</aside>', '', body, flags=re.DOTALL)
    body = re.sub(r'class="sidebar[^"]*".*?</div>', '', body, flags=re.DOTALL)
    return body.strip()

def html_to_tiptap_json(html_content):
    """Convert simple HTML to TipTap-compatible JSON structure."""
    if not html_content:
        return {"type": "doc", "content": [{"type": "paragraph"}]}
    
    # Parse simple HTML blocks
    blocks = []
    # Split by block-level tags
    parts = re.split(r'(</?(?:p|h[1-6]|ul|ol|blockquote|pre|hr|div|section|figure)\b[^>]*>)', html_content, flags=re.DOTALL)
    
    current_tag = None
    current_content = []
    
    for part in parts:
        part = part.strip()
        if not part:
            continue
        
        open_match = re.match(r'<(p|h[1-6]|ul|ol|blockquote|pre|hr|div|section|figure)\b[^>]*>', part)
        close_match = re.match(r'</(p|h[1-6]|ul|ol|blockquote|pre|hr|div|section|figure)>', part)
        
        if open_match:
            current_tag = open_match.group(1)
            current_content = []
        elif close_match and current_tag:
            inner = "".join(current_content).strip()
            node = html_to_node(current_tag, inner)
            if node:
                blocks.append(node)
            current_tag = None
            current_content = []
        elif current_tag:
            current_content.append(part)
        elif part.strip():
            # Text without wrapper - wrap in paragraph
            text = strip_tags(part)
            if text.strip():
                blocks.append({
                    "type": "paragraph",
                    "content": [{"type": "text", "text": text.strip()}]
                })
    if not blocks:
        blocks.append({"type": "paragraph"})
    
    # Drop empty text nodes and empty paragraphs
    clean_blocks = []
    for block in blocks:
        if not block:
            continue
        content = block.get("content")
        if content and all(
            isinstance(c, dict) and c.get("type") == "text" and not c.get("text")
            for c in content
        ):
            continue
        clean_blocks.append(block)
    blocks = clean_blocks or [{"type": "paragraph"}]
    
    return {"type": "doc", "content": blocks}

def html_to_node(tag, inner):
    """Convert a single HTML tag + content to a TipTap node."""
    text = strip_tags(inner).strip()

    if tag == "p":
        if not text:
            return None
        return {"type": "paragraph", "content": [{"type": "text", "text": text}]}
    elif tag.startswith("h") and len(tag) == 2:
        level = int(tag[1])
        return {"type": "heading", "attrs": {"level": level}, "content": [{"type": "text", "text": text}]}
    elif tag == "hr":
        return {"type": "horizontalRule"}
    else:
        if not text:
            return None
        return {"type": "paragraph", "content": [{"type": "text", "text": text}]}

def strip_tags(html_text):
    """Remove HTML tags from text."""
    clean = re.sub(r'<[^>]+>', '', html_text)
    clean = html_module.unescape(clean)
    return clean

def slugify(text):
    slug = text.lower().strip()
    slug = re.sub(r'[^\w\s-]', '', slug)
    slug = re.sub(r'[\s_]+', '-', slug)
    slug = re.sub(r'-+', '-', slug)
    slug = slug.strip('-')[:200]
    return slug or "page"

def is_cms_page(body):
    """Skip if this page already has CMS content injection."""
    return 'data-cms-slug' in body

def import_file(filepath, token, content_type="blog", dry_run=False):
    """Import a single HTML file as a CMS page."""
    filename = os.path.basename(filepath)
    rel_path = os.path.relpath(filepath, FRONTEND_DIR)
    
    with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
        content = f.read()
    
    if is_cms_page(content):
        return None  # Skip CMS-powered pages
    
    title = extract_title_from_html(content, filename)
    description = extract_description_from_html(content)
    body_html = extract_body_html(content)
    content_json = html_to_tiptap_json(body_html)
    
    # Generate slug from filename
    slug = filename.replace(".html", "").lower()
    slug = re.sub(r'[^a-z0-9-]', '-', slug)
    slug = re.sub(r'-+', '-', slug)
    
    # Determine content type
    if "glossary" in rel_path:
        ctype = "glossary"
    elif "blog" in rel_path:
        ctype = "blog"
    else:
        ctype = "page"
    
    # Extract tags from breadcrumbs or categories
    tags = ctype
    if "glossary" in rel_path:
        tags = "glossary"
    
    payload = {
        "slug": slug,
        "title": title[:500],
        "description": description[:500] if description else None,
        "content_json": content_json,
        "status": "published",
        "content_type": ctype,
        "tags": tags,
        "change_note": f"Imported from {rel_path}",
    }
    
    if dry_run:
        print(f"  [DRY RUN] Would import: {title} -> {slug}")
        return None
    
    result = cms_request("POST", "/api/v1/cms/pages", payload, token)
    if result:
        print(f"  IMPORTED: {title} (/{slug}) [{ctype}]")
        return result
    else:
        print(f"  FAILED: {title} (/{slug}) - may already exist or error")
        return None

def main():
    dry_run = "--dry-run" in sys.argv
    
    print("=" * 60)
    print("Importing blogs and glossary pages to CMS")
    print("=" * 60)
    
    token = get_token()
    print(f"Authenticated: {AUTH_EMAIL}")
    
    blog_dir = os.path.join(FRONTEND_DIR, "blog")
    glossary_dir = os.path.join(FRONTEND_DIR, "glossary")
    
    imported = 0
    skipped = 0
    failed = 0
    
    # Import blog posts
    if os.path.isdir(blog_dir):
        print(f"\n--- Blog Posts ({blog_dir}) ---")
        for f in sorted(glob.glob(os.path.join(blog_dir, "*.html"))):
            # Skip index.html
            if f.endswith("index.html"):
                continue
            result = import_file(f, token, "blog", dry_run)
            if result:
                imported += 1
            elif result is None:
                skipped += 1
            else:
                failed += 1
    
    # Import glossary pages
    if os.path.isdir(glossary_dir):
        print(f"\n--- Glossary Pages ({glossary_dir}) ---")
        for f in sorted(glob.glob(os.path.join(glossary_dir, "*.html"))):
            if f.endswith("index.html"):
                continue
            result = import_file(f, token, "glossary", dry_run)
            if result:
                imported += 1
            elif result is None:
                skipped += 1
            else:
                failed += 1
    
    print(f"\n{'=' * 60}")
    print(f"Summary: {imported} imported, {skipped} skipped, {failed} failed")
    if dry_run:
        print("(dry run - no changes made)")
    print(f"{'=' * 60}")

if __name__ == "__main__":
    main()
