"""
One-off: strip empty text nodes from existing CMS page content_json,
and regenerate content_html from the cleaned JSON. Requires CMS server not
needed — uses DB directly. Run from backend/ with JWT_SECRET set.
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from database import SessionLocal
from models import CMSPage, CMSPageRevision

HTML_TAG_MAP = {
    "paragraph": "p",
    "heading": "h{level}",
    "blockquote": "blockquote",
    "codeBlock": "pre",
    "bulletList": "ul",
    "orderedList": "ol",
    "listItem": "li",
    "horizontalRule": "hr",
}


def clean_text_nodes(node):
    if not node or not isinstance(node, dict):
        return None
    out = {"type": node["type"]}
    if node.get("attrs"):
        out["attrs"] = node["attrs"]
    if node.get("marks"):
        out["marks"] = node["marks"]
    if "text" in node:
        if node.get("text"):
            out["text"] = node["text"]
        else:
            return None
        return out
    if node.get("content"):
        cleaned = [clean_text_nodes(c) for c in node["content"]]
        cleaned = [c for c in cleaned if c]
        if cleaned:
            out["content"] = cleaned
    return out


def json_to_html(node):
    if not node:
        return ""
    t = node.get("type")
    if t == "text":
        marks = node.get("marks") or []
        text = node.get("text", "")
        for m in marks:
            mt = m.get("type")
            if mt == "bold":
                text = f"<strong>{text}</strong>"
            elif mt == "italic":
                text = f"<em>{text}</em>"
            elif mt == "underline":
                text = f"<u>{text}</u>"
            elif mt == "strike":
                text = f"<s>{text}</s>"
            elif mt == "code":
                text = f"<code>{text}</code>"
        return text
    if t == "doc":
        return "".join(json_to_html(c) for c in node.get("content", []))
    if t == "hardBreak":
        return "<br>"
    content_html = "".join(json_to_html(c) for c in node.get("content", []))
    tag = HTML_TAG_MAP.get(t)
    if not tag:
        return content_html
    if "{" in tag:
        tag = tag.format(level=node.get("attrs", {}).get("level", 1))
    if t == "listItem":
        return f"<li>{content_html}</li>"
    if t in ("bulletList", "orderedList"):
        return f"<{tag}>{content_html}</{tag}>"
    if t == "horizontalRule":
        return "<hr>"
    return f"<{tag}>{content_html}</{tag}>"


def main():
    db = SessionLocal()
    fixed = 0
    for page in db.query(CMSPage).all():
        cj = page.content_json
        if not cj or not isinstance(cj, dict):
            continue
        cleaned = clean_text_nodes(cj)
        if cleaned is None:
            cleaned = {"type": "doc", "content": []}
        raw = cleaned
        if cleaned != cj:
            page.content_json = cleaned
            page.content_html = json_to_html(cleaned)
            fixed += 1
            print(f"FIXED: {page.slug}")
    db.commit()
    # Fix latest published revisions too
    for rev in db.query(CMSPageRevision).all():
        cj = rev.content_json
        if not cj or not isinstance(cj, dict):
            continue
        cleaned = clean_text_nodes(cj)
        if cleaned is None:
            cleaned = {"type": "doc", "content": []}
        if cleaned != cj:
            rev.content_json = cleaned
            rev.content_html = json_to_html(cleaned)
            fixed += 1
            print(f"FIXED revision: {rev.page_id}")
    db.commit()
    print(f"\nTotal rows fixed: {fixed}")
    db.close()


if __name__ == "__main__":
    main()
