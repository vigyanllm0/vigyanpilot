import re, json, urllib.request

API = "http://localhost:8001"

def api(method, path, data=None, token=None):
    url = API + path
    body = json.dumps(data).encode() if data else None
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    r = urllib.request.urlopen(urllib.request.Request(url, data=body, headers=headers, method=method))
    return json.loads(r.read())

def main():
    # Login as admin
    r = api("POST", "/api/v1/cms/auth/login", {"email": "admin@vigyanllm.in", "password": "admin123"})
    token = r["token"]
    print("Logged in ✅")

    html = open("../frontend/blog/index.html", encoding="utf-8").read()
    
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
