import re, json, urllib.request, os, sys

API = os.environ.get("CMS_API_URL", "http://localhost:8001")
ADMIN_EMAIL = os.environ.get("CMS_ADMIN_EMAIL")
ADMIN_PASSWORD = os.environ.get("CMS_ADMIN_PASSWORD")

if not ADMIN_EMAIL or not ADMIN_PASSWORD:
    print("FATAL: Set CMS_ADMIN_EMAIL and CMS_ADMIN_PASSWORD environment variables", file=sys.stderr)
    sys.exit(1)

def api(method, path, data=None, token=None):
    url = API + path
    body = json.dumps(data).encode() if data else None
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    with urllib.request.urlopen(urllib.request.Request(url, data=body, headers=headers, method=method), timeout=30) as r:
        raw = r.read()
    try:
        return json.loads(raw)
    except json.JSONDecodeError as e:
        print(f"API returned non-JSON: {raw[:200]}", file=sys.stderr)
        raise

def main():
    # Login as admin (credentials from environment)
    r = api("POST", "/api/v1/cms/auth/login", {"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD})
    token = r["token"]
    print("Logged in ✅")

    with open("../frontend/blog/index.html", encoding="utf-8") as f:
        html = f.read()
    
    pattern = re.compile(
        r'<article class="blog-card">'
        r'.*?<span class="blog-tag (tag-\w+)">(.*?)</span>'
        r'.*?<span class="read-time">(.*?)</span>'
        r'.*?<h3>(.*?)</h3>'
        r'.*?<p>(.*?)</p>'
        r'.*?href="/blog/(.*?)"'
        r'.*?</article>',
        re.DOTALL
    )

    cat_map = {
        "tag-primer": "Primer Design",
        "tag-qpcr": "qPCR & TaqMan",
        "tag-advanced": "Advanced",
        "tag-india": "India Research",
        "tag-ai": "AI & ML"
    }

    success = 0
    skipped = 0
    failed = 0

    for m in pattern.finditer(html):
        tag_class = m.group(1)
        category = cat_map.get(tag_class, "General")
        date_str = m.group(3).strip()
        title = m.group(4).strip()
        desc = m.group(5).strip()
        slug = m.group(6).strip()

        months = ['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec']
        try:
            month_num = months.index(date_str.split()[0]) + 1
        except (ValueError, IndexError):
            month_num = 1
        pub_date = f"2025-{month_num:02d}-01T00:00:00Z"

        payload = {
            "slug": slug,
            "title": title,
            "description": desc,
            "content_type": "blog",
            "status": "draft",
            "content_json": {
                "type": "doc",
                "content": [{"type": "paragraph", "content": [{"type": "text", "text": desc}]}]
            }
        }

        try:
            api("POST", "/api/v1/cms/pages", payload, token)
        except urllib.error.HTTPError as e:
            body = e.read().decode()
            if "already exists" in body.lower():
                print(f"  SKIP {slug} (exists)")
                skipped += 1
                continue
            print(f"  FAIL {slug}: {body[:100]}")
            failed += 1
            continue

        try:
            api("POST", f"/api/v1/cms/pages/{slug}/submit", {}, token)
            api("POST", f"/api/v1/cms/pages/{slug}/approve", {}, token)
            print(f"  OK {slug}")
            success += 1
        except urllib.error.HTTPError as e:
            body = e.read().decode()
            print(f"  FAIL {slug} after create: {body[:100]}")
            failed += 1

    print(f"\n✅ Imported: {success}  ⏭️  Skipped: {skipped}  ❌ Failed: {failed}")
    if skipped:
        print("(already in CMS — likely from previous import run)")

if __name__ == "__main__":
    main()
