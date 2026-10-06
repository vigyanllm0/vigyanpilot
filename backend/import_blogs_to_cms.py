"""
Import all existing blog posts and glossary pages into the CMS.

Converts each static HTML file's <main> content (fallback: whole body with
site chrome removed) into TipTap JSON that round-trips through the CMS editor
(frontend/cms-editor.html: StarterKit heading levels [2,3], Underline, Link,
ResizableImage, Table/Row/Cell/Header) and renders via backend/routes/pages.py
_render_node().

Fidelity rules (measured against the 305 content files):
  - inline: <a> link mark, <strong>/<b>, <em>/<i>, <u>, <s>/<del>, <code>, <br>
  - blocks: p, h2/h3 (h1 dropped = page title is a field; h4-h6 demoted to h3),
    ul/ol -> bulletList/orderedList, blockquote, pre -> codeBlock, hr,
    table -> table/tableRow/tableHeader/tableCell (renderer supports them),
    figure/img -> image node (caption/align), details/summary flattened to
    bold-Q paragraphs + answer blocks (editor has no details node),
    <sup>/<sub> converted to unicode super/subscript (no sup node in editor)
  - chrome dropped: nav/footer/aside/header-at-body-level, scripts, styles,
    noscript (GTM), iframes, buttons, forms, svgs, .toc, .article-meta-bar,
    .author-bio, .mobile-menu
  - never emits empty text nodes (known editor breaker)

Usage:
  cd backend && CMS_URL=http://localhost:8001 CMS_ADMIN_EMAIL=... \\
      AUTH_PASSWORD=... python3 import_blogs_to_cms.py [--dry-run] [--limit N]

Requires CMS_ADMIN_EMAIL / AUTH_PASSWORD env vars (the seeded CMS admin).
"""

import glob
import html as html_module
import json
import os
import re
import sys
import urllib.error
import urllib.request
from html.parser import HTMLParser

CMS_URL = os.environ.get("CMS_URL", "http://localhost:8001")
AUTH_EMAIL = os.environ.get("CMS_ADMIN_EMAIL") or os.environ.get("AUTH_EMAIL", "contact@vigyanllm.in")
AUTH_PASSWORD = os.environ.get("CMS_ADMIN_PASSWORD") or os.environ.get("AUTH_PASSWORD")
if not AUTH_PASSWORD:
    print("ERROR: CMS_ADMIN_PASSWORD (or AUTH_PASSWORD) env var required")
    sys.exit(1)
FRONTEND_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "frontend")
_ALLOWED_SCHEMES = {"http", "https"}

# Tags whose entire subtree is page chrome or not renderable by the editor.
_DROP_TAGS = {
    "script", "style", "noscript", "nav", "footer", "aside", "iframe",
    "button", "form", "svg", "input", "select", "textarea", "object",
    "embed", "video", "audio", "canvas", "template",
}
_VOID_TAGS = {"br", "img", "hr", "meta", "input", "link", "source", "area", "base", "col", "embed", "track", "wbr"}
# Site chrome sitting directly under <body> in pages that have no <main>.
_BODY_CHROME = {"header", "footer", "nav", "aside"}
_DROP_IDS = {"mobile-menu", "hamburger"}
_DROP_CLASS_TOKENS = {"toc", "article-meta-bar", "author-bio"}
_TRANSPARENT_TAGS = {
    "div", "section", "main", "article", "header", "span", "center", "font",
    "abbr", "mark", "small", "q", "cite", "label", "dl", "dt", "dd", "figure",
}
_HEADING_LEVELS = {"h1", "h2", "h3", "h4", "h5", "h6"}
_SUP_MAP = str.maketrans("0123456789+-=()n", "⁰¹²³⁴⁵⁶⁷⁸⁹⁺⁻⁼⁽⁾ⁿ")
_SUB_MAP = str.maketrans("0123456789+-=()n", "₀₁₂₃₄₅₆₇₈₉₊₋₌₍₎ₙ")


# ── HTTP helpers ──────────────────────────────────────────────────────────

def _safe_urlopen(req, timeout=30):
    if req.get_full_url().split(":", 1)[0].lower() not in _ALLOWED_SCHEMES:
        raise ValueError(f"Disallowed URL scheme: {req.get_full_url()}")
    return urllib.request.urlopen(req, timeout=timeout)  # noqa: S310


def get_token():
    data = json.dumps({"email": AUTH_EMAIL, "password": AUTH_PASSWORD}).encode()
    req = urllib.request.Request(  # noqa: S310
        f"{CMS_URL}/api/v1/cms/auth/login",
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    resp = _safe_urlopen(req)
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
    req = urllib.request.Request(  # noqa: S310
        f"{CMS_URL}{path}",
        data=data,
        headers=headers,
        method=method,
    )
    try:
        resp = _safe_urlopen(req)
        return json.loads(resp.read()), resp.status
    except urllib.error.HTTPError as e:
        err = e.read().decode()
        print(f"  HTTP {e.code}: {err[:200]}")
        return None, e.code


# ── HTML tree parsing ─────────────────────────────────────────────────────

class _El:
    __slots__ = ("attrs", "children", "tag")

    def __init__(self, tag, attrs=None):
        self.tag = tag
        self.attrs = dict(attrs or {})
        self.children = []  # list[_El | str]


class _TreeParser(HTMLParser):
    """Parse an HTML fragment into a tree of _El / str nodes."""

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.root = _El("#root")
        self._stack = [self.root]

    def handle_starttag(self, tag, attrs):
        el = _El(tag, attrs)
        self._stack[-1].children.append(el)
        if tag not in _VOID_TAGS:
            self._stack.append(el)

    def handle_startendtag(self, tag, attrs):
        if tag not in _VOID_TAGS:
            el = _El(tag, attrs)
            self._stack[-1].children.append(el)
        else:
            self._stack[-1].children.append(_El(tag, attrs))

    def handle_endtag(self, tag):
        if tag in _VOID_TAGS:
            return
        for i in range(len(self._stack) - 1, 0, -1):
            if self._stack[i].tag == tag:
                del self._stack[i:]
                return

    def handle_data(self, data):
        if data:
            self._stack[-1].children.append(data)


def _parse(html_content):
    parser = _TreeParser()
    try:
        parser.feed(html_content)
        parser.close()
    except Exception:  # noqa: BLE001 — malformed markup: keep whatever parsed
        pass
    return parser.root


def _class_tokens(el):
    return set((el.attrs.get("class") or "").split())


def _drop_node(el):
    """True if this element's subtree is chrome / unrenderable."""
    if el.tag in _DROP_TAGS:
        return True
    if el.attrs.get("id") in _DROP_IDS:
        return True
    tokens = _class_tokens(el)
    return bool(tokens & _DROP_CLASS_TOKENS)


def _find_main(el):
    if isinstance(el, _El):
        if el.tag == "main":
            return el
        for c in el.children:
            found = _find_main(c)
            if found is not None:
                return found
    return None


def _collapse_ws(text):
    return re.sub(r"[ \t\r\n\f]+", " ", text)


def _norm(text):
    return _collapse_ws(text or "").strip().lower().rstrip("|").strip()


# ── Inline conversion (marks) ─────────────────────────────────────────────

def _safe_href(href):
    href = (href or "").strip()
    if not href:
        return None
    low = href.lower().split(":", 1)[0]
    if low in ("javascript", "data", "vbscript"):
        return None
    if low in ("http", "https", "mailto") or href.startswith(("/", "#")):
        return href
    # bare domains / relative paths without scheme
    if " " not in href:
        return href
    return None


def _flatten_text(el, translate=None):
    """All descendant text (chrome excluded), optionally unicode-translated."""
    parts: list[str] = []

    def walk(node):
        if isinstance(node, str):
            parts.append(node)
            return
        if node.tag in _DROP_TAGS:
            return
        if node.tag in ("sup", "sub"):
            # collect the subtree's raw text once, then map it (no re-entry)
            m = _SUP_MAP if node.tag == "sup" else _SUB_MAP
            inner: list[str] = []

            def sub_walk(n):
                if isinstance(n, str):
                    inner.append(n)
                    return
                if n.tag in _DROP_TAGS:
                    return
                for cc in n.children:
                    sub_walk(cc)

            sub_walk(node)
            parts.append("".join(inner).translate(m))
            return
        for c in node.children:
            walk(c)

    walk(el)
    text = _collapse_ws("".join(parts))
    if translate:
        text = text.translate(translate)  # noqa: PLR1714 — idempotent map
    return text


def _raw_text(el):
    """Descendant text with newlines preserved (for code blocks)."""
    parts: list[str] = []

    def walk(node):
        if isinstance(node, str):
            parts.append(node)
            return
        if node.tag in _DROP_TAGS:
            return
        for c in node.children:
            walk(c)

    walk(el)
    return "".join(parts)


def _inline_nodes(children, marks=()):
    """Convert inline content to a list of TipTap inline nodes.

    Whitespace-only runs BETWEEN content runs are preserved (they are real
    separating spaces); outer whitespace is trimmed from the ends only.
    """
    runs: list[list] = []  # [marks-key, text]; "" key = no marks
    nodes: list[dict] = []

    def emit():
        merged: list[list] = []
        for key, text in runs:
            if merged and merged[-1][0] == key:
                merged[-1][1] += text
            else:
                merged.append([key, text])
        runs.clear()
        for key, text in merged:
            if not text:
                continue
            if key == "":
                nodes.append({"type": "text", "text": text})
            else:
                nodes.append({"type": "text", "text": text, "marks": json.loads(key)})

    def run(text, active_marks):
        if text:
            key = (
                json.dumps([m for _i, m in active_marks], sort_keys=True, separators=(",", ":"))
                if active_marks else ""
            )
            runs.append([key, text])

    def walk(kids, active_marks):
        for c in kids:
            if isinstance(c, str):
                run(_collapse_ws(c), active_marks)
                continue
            tag = c.tag
            if tag in _DROP_TAGS:
                continue
            new_marks = active_marks
            if tag in ("strong", "b"):
                new_marks = [*active_marks, (len(active_marks), {"type": "bold"})]
            elif tag in ("em", "i"):
                new_marks = [*active_marks, (len(active_marks), {"type": "italic"})]
            elif tag == "u":
                new_marks = [*active_marks, (len(active_marks), {"type": "underline"})]
            elif tag in ("s", "del", "strike"):
                new_marks = [*active_marks, (len(active_marks), {"type": "strike"})]
            elif tag == "code":
                new_marks = [*active_marks, (len(active_marks), {"type": "code"})]
            elif tag == "a":
                href = _safe_href(c.attrs.get("href"))
                if href:
                    new_marks = [*active_marks, (len(active_marks), {"type": "link", "attrs": {"href": href}})]
            elif tag == "br":
                emit()
                nodes.append({"type": "hardBreak"})
                continue
            elif tag in ("sup", "sub"):
                m = _SUP_MAP if tag == "sup" else _SUB_MAP
                run(_flatten_text(c, m), active_marks)
                continue
            walk(c.children, new_marks)

    walk(children, tuple((i, m) for i, m in enumerate(marks)))
    emit()
    # trim outer whitespace from the ends only (internal spaces are content)
    if nodes and nodes[0].get("type") == "text":
        nodes[0]["text"] = nodes[0]["text"].lstrip()
    if nodes and nodes[-1].get("type") == "text":
        nodes[-1]["text"] = nodes[-1]["text"].rstrip()
    nodes = [n for n in nodes if n.get("type") != "text" or n.get("text")]
    return nodes


def _inline_text(children):
    return _collapse_ws("".join(
        c if isinstance(c, str) else _flatten_text(c) for c in children
    )).strip()


def _paragraph(children):
    node = {"type": "paragraph"}
    nodes = _inline_nodes(children)
    if nodes:
        node["content"] = nodes
    return node


def _empty_paragraph():
    return {"type": "paragraph"}


# ── Block conversion ──────────────────────────────────────────────────────

def _blocks(el, skip_h1=True):
    """Convert an element (or whitespace string) to a list of block nodes."""
    if isinstance(el, str):
        text = _collapse_ws(el).strip()
        if text:
            return [{"type": "paragraph", "content": [{"type": "text", "text": text}]}]
        return []
    if _drop_node(el):
        return []
    tag = el.tag

    if tag in _TRANSPARENT_TAGS or tag in _BODY_CHROME:
        out = []
        for c in el.children:
            out.extend(_blocks(c, skip_h1))
        return out
    if tag in ("p",):
        # split out images/figures (block-level nodes) keeping document order
        parts: list = []  # ("t", children-list) | ("n", block-node)
        buf: list = []
        for c in el.children:
            if isinstance(c, _El) and c.tag in ("img", "figure"):
                if buf:
                    parts.append(("t", buf))
                    buf = []
                node = _figure_node(c) if c.tag == "figure" else _image_node(c)
                if node is not None:
                    parts.append(("n", node))
            else:
                buf.append(c)
        if buf:
            parts.append(("t", buf))
        out = []
        for kind, val in parts:
            if kind == "n":
                out.append(val)
                continue
            nodes = _inline_nodes(val)
            if any(n.get("type") == "hardBreak" or (n.get("type") == "text" and n.get("text", "").strip())
                   for n in nodes):
                out.append({"type": "paragraph", "content": nodes})
        return out
    if tag in _HEADING_LEVELS:
        if tag == "h1" and skip_h1:
            return []  # page title lives in the title field (rendered separately)
        level = int(tag[1])
        level = 2 if level <= 2 else 3  # editor schema: heading levels [2,3]
        text = _inline_text(el.children)
        if not text:
            return []
        return [{"type": "heading", "attrs": {"level": level}, "content": _inline_nodes(el.children)}]
    if tag in ("ul", "ol"):
        items = []
        for c in el.children:
            if isinstance(c, _El) and c.tag == "li":
                item_blocks = _blocks(c, skip_h1)
                if item_blocks:
                    items.append({"type": "listItem", "content": item_blocks})
            elif isinstance(c, str) and c.strip():
                items.append({
                    "type": "listItem",
                    "content": [{"type": "paragraph", "content": [{"type": "text", "text": _collapse_ws(c).strip()}]}],
                })
        if not items:
            return []
        return [{"type": "bulletList" if tag == "ul" else "orderedList", "content": items}]
    if tag == "li":  # stray li outside a list wrapper
        inner = []
        for c in el.children:
            inner.extend(_blocks(c, skip_h1))
        return inner or [_empty_paragraph()]
    if tag == "blockquote":
        inner = []
        for c in el.children:
            inner.extend(_blocks(c, skip_h1))
        return [{"type": "blockquote", "content": inner}] if inner else []
    if tag == "pre":
        code_el = next((c for c in el.children if isinstance(c, _El) and c.tag == "code"), None)
        raw = _raw_text(code_el if code_el is not None else el).strip("\n")
        if not raw.strip():
            return []
        lang = ""
        cls = (code_el.attrs.get("class") or "") if code_el is not None else ""
        m = re.search(r"language-([\w+-]+)", cls)
        if m:
            lang = m.group(1)
        # codeBlock content = text* — newlines live inside ONE text node
        node = {"type": "codeBlock", "content": [{"type": "text", "text": raw}]}
        if lang:
            node["attrs"] = {"language": lang}
        return [node]
    if tag == "hr":
        return [{"type": "horizontalRule"}]
    if tag == "table":
        return _table_nodes(el)
    if tag == "figure":
        node = _figure_node(el)
        if node is not None:
            return [node]
        inner = []
        for c in el.children:
            inner.extend(_blocks(c, skip_h1))
        return inner
    if tag == "img":
        node = _image_node(el)
        return [node] if node else []
    if tag == "details":
        out = []
        for c in el.children:
            if isinstance(c, _El) and c.tag == "summary":
                text = _inline_text(c.children)
                if text:
                    out.append({
                        "type": "paragraph",
                        "content": [{"type": "text", "text": text, "marks": [{"type": "bold"}]}],
                    })
            else:
                out.extend(_blocks(c, skip_h1))
        return out
    if tag == "summary":  # standalone summary (rare)
        text = _inline_text(el.children)
        if text:
            return [{
                "type": "paragraph",
                "content": [{"type": "text", "text": text, "marks": [{"type": "bold"}]}],
            }]
        return []
    # unknown element at block level: transparent (its children carry content)
    out = []
    for c in el.children:
        out.extend(_blocks(c, skip_h1))
    return out


def _image_node(el, caption="", align=""):
    src = (el.attrs.get("src") or "").strip()
    if not src or src.startswith("data:"):
        return None
    node = {
        "type": "image",
        "attrs": {
            "src": src,
            "alt": el.attrs.get("alt") or "",
            "loading": "lazy",
        },
    }
    if el.attrs.get("title"):
        node["attrs"]["title"] = el.attrs["title"]
    if caption:
        node["attrs"]["caption"] = caption
    if align:
        node["attrs"]["align"] = align
    return node


def _find_align(el):
    tokens = _class_tokens(el)
    for a in ("left", "right", "center"):
        if f"vl-align-{a}" in tokens or f"align-{a}" in tokens or f"align{a}" in tokens:
            return a
    align_attr = (el.attrs.get("align") or "").strip().lower()
    return align_attr if align_attr in ("left", "right", "center") else ""


def _figure_node(fig):
    img = None

    def find(node):
        nonlocal img
        if isinstance(node, _El):
            if node.tag == "img":
                img = node
                return
            for c in node.children:
                find(c)

    find(fig)
    caption = ""
    align = _find_align(fig)
    for c in fig.children:
        if isinstance(c, _El) and c.tag == "figcaption":
            caption = _inline_text(c.children)
    if img is None:
        return None
    if not align:
        align = _find_align(img)
    return _image_node(img, caption=caption, align=align)


def _table_nodes(table):
    rows = []

    def collect(node):
        if isinstance(node, _El):
            if _drop_node(node):
                return
            if node.tag == "tr":
                rows.append(node)
                return
            for c in node.children:
                collect(c)

    collect(table)
    row_nodes = []
    for tr in rows:
        cell_nodes = []
        for c in tr.children:
            if isinstance(c, _El) and c.tag in ("td", "th"):
                cell_blocks = _blocks(c)
                cell_blocks = cell_blocks or [_empty_paragraph()]
                node = {"type": "tableCell" if c.tag == "td" else "tableHeader"}
                attrs = {}
                try:
                    colspan = int(c.attrs.get("colspan", 1) or 1)
                    rowspan = int(c.attrs.get("rowspan", 1) or 1)
                except (TypeError, ValueError):
                    colspan, rowspan = 1, 1
                if colspan > 1:
                    attrs["colspan"] = colspan
                if rowspan > 1:
                    attrs["rowspan"] = rowspan
                if attrs:
                    node["attrs"] = attrs
                node["content"] = cell_blocks
                cell_nodes.append(node)
        if cell_nodes:
            row_nodes.append({"type": "tableRow", "content": cell_nodes})
    if not row_nodes:
        return []
    return [{"type": "table", "content": row_nodes}]


# ── Document assembly ─────────────────────────────────────────────────────

def extract_body_html(content):
    """Prefer <main> content; fall back to <body> (chrome dropped during walk)."""
    m = re.search(r"<body[^>]*>(.*?)</body>", content, re.DOTALL | re.IGNORECASE)
    return m.group(1) if m else content


def html_to_tiptap_json(html_content, title="", description=""):
    """Convert an HTML fragment to a TipTap doc honoring the editor schema."""
    if not html_content:
        return {"type": "doc", "content": [_empty_paragraph()]}

    root = _parse(html_content)
    main = _find_main(root)
    start = main if main is not None else root

    if main is None:
        # no <main>: drop site chrome that sits directly under body
        filtered = []
        for c in start.children:
            if isinstance(c, _El) and (c.tag in _BODY_CHROME or c.attrs.get("id") in _DROP_IDS
                                       or c.attrs.get("id") == "mobile-menu"):
                continue
            filtered.append(c)
        start_children = filtered
    else:
        start_children = start.children

    blocks = []
    for c in start_children:
        blocks.extend(_blocks(c))

    # drop a leading paragraph that merely repeats the meta description
    if description:
        desc_key = _norm(description)
        for i, b in enumerate(blocks[:3]):
            if b.get("type") == "paragraph" and _norm(_plain_text(b)) == desc_key:
                blocks.pop(i)
                break

    blocks = [b for b in blocks if b]
    if not blocks:
        blocks = [_empty_paragraph()]

    # empty text nodes are a known editor breaker — final safety pass
    def scrub(node):
        if not isinstance(node, dict):
            return
        content = node.get("content")
        if isinstance(content, list):
            node["content"] = [
                c for c in content
                if not (isinstance(c, dict) and c.get("type") == "text" and not (c.get("text") or "").strip())
            ] or ([_empty_paragraph()["content"]] if node.get("type") != "text" else [])
            for c in node["content"]:
                scrub(c)

    doc = {"type": "doc", "content": blocks}
    scrub(doc)
    if not doc["content"]:
        doc["content"] = [_empty_paragraph()]
    return doc


def _plain_text(node):
    parts = []

    def walk(n):
        if isinstance(n, dict):
            if n.get("type") == "text":
                parts.append(n.get("text", ""))
            for c in n.get("content") or []:
                walk(c)

    walk(node)
    return "".join(parts)


def extract_title_from_html(content, filename):
    """Extract <title> from HTML, fallback to filename."""
    m = re.search(r"<title>(.*?)</title>", content, re.DOTALL)
    if m:
        return html_module.unescape(m.group(1)).strip()
    return filename.replace(".html", "").replace("-", " ").title()


def extract_description_from_html(content):
    """Extract meta description."""
    m = re.search(r'<meta\s+name=["\']description["\']\s+content=["\'](.*?)["\']', content, re.DOTALL)
    if m:
        return html_module.unescape(m.group(1)).strip()
    return ""


def slugify(text):
    slug = text.lower().strip()
    slug = re.sub(r"[^\w\s-]", "", slug)
    slug = re.sub(r"[\s_]+", "-", slug)
    slug = re.sub(r"-+", "-", slug)
    slug = slug.strip("-")[:200]
    return slug or "page"


def is_cms_page(body):
    """Skip if this page already has CMS content injection."""
    return "data-cms-slug" in body


def import_file(filepath, token, content_type="blog", dry_run=False):
    """Import a single HTML file as a CMS page."""
    filename = os.path.basename(filepath)
    rel_path = os.path.relpath(filepath, FRONTEND_DIR)

    with open(filepath, encoding="utf-8", errors="ignore") as f:
        content = f.read()

    if is_cms_page(content):
        return None  # Skip CMS-powered pages

    title = extract_title_from_html(content, filename)
    description = extract_description_from_html(content)
    body_html = extract_body_html(content)
    content_json = html_to_tiptap_json(body_html, title=title, description=description)

    # Generate slug from filename
    slug = filename.replace(".html", "").lower()
    slug = re.sub(r"[^a-z0-9-]", "-", slug)
    slug = re.sub(r"-+", "-", slug)

    # Determine content type
    if "glossary" in rel_path:
        ctype = "glossary"
    elif "blog" in rel_path:
        ctype = "blog"
    else:
        ctype = "page"

    payload = {
        "slug": slug,
        "title": title[:500],
        "description": description[:500] if description else None,
        "content_json": content_json,
        "status": "published",
        "content_type": ctype,
        "tags": ctype,
        "change_note": f"Imported from {rel_path}"[:255],
    }

    if dry_run:
        blocks = len(content_json.get("content", []))
        print(f"  [DRY RUN] {title[:70]} -> /{slug} [{ctype}] ({blocks} blocks)")
        return None

    result, status = cms_request("POST", "/api/v1/cms/pages", payload, token)
    if result:
        print(f"  IMPORTED: {title[:70]} (/{slug}) [{ctype}]")
        return "imported"
    if status == 409:
        print(f"  EXISTS: {slug}")
        return "exists"
    print(f"  FAILED: {title[:70]} (/{slug}) - HTTP {status}")
    return "failed"


def main():
    dry_run = "--dry-run" in sys.argv
    limit = 0
    if "--limit" in sys.argv:
        try:
            limit = int(sys.argv[sys.argv.index("--limit") + 1])
        except (ValueError, IndexError):
            print("ERROR: --limit expects an integer")
            sys.exit(2)

    print("=" * 60)
    print("Importing blogs and glossary pages to CMS")
    print(f"Target: {CMS_URL}")
    print("=" * 60)

    token = get_token()
    print(f"Authenticated: {AUTH_EMAIL}")

    blog_dir = os.path.join(FRONTEND_DIR, "blog")
    glossary_dir = os.path.join(FRONTEND_DIR, "glossary")

    imported = 0
    skipped = 0
    failed = 0

    def run_dir(directory, ctype):
        nonlocal imported, skipped, failed
        if not os.path.isdir(directory):
            return
        print(f"\n--- {ctype.title()}s ({directory}) ---")
        files = [f for f in sorted(glob.glob(os.path.join(directory, "*.html")))
                 if not f.endswith("index.html")]
        if limit:
            files = files[:limit]
        for f in files:
            result = import_file(f, token, ctype, dry_run)
            if result == "imported":
                imported += 1
            elif result == "exists":
                skipped += 1
            elif result == "failed":
                failed += 1
            else:
                skipped += 1

    run_dir(blog_dir, "blog")
    run_dir(glossary_dir, "glossary")

    print(f"\n{'=' * 60}")
    print(f"Summary: {imported} imported, {skipped} skipped, {failed} failed")
    if dry_run:
        print("(dry run - no changes made)")
    print("=" * 60)
    if failed:
        sys.exit(1)


if __name__ == "__main__":
    main()
