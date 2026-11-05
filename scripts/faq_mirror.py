#!/usr/bin/env python3
"""FAQ mirror gate — verify FAQPage schema matches the page's visible text.

The site rule: every FAQPage JSON-LD question AND answer must appear in the
page's visible text, character-exact (after link-text flattening), and the
microdata FAQPage (when present) must equal the JSON-LD block. Schema-only
FAQs = a mirror violation (see docs/seo-week3/ticket-faq-schema-only-37.md).

Usage:
    python3 scripts/faq_mirror.py                # scan all frontend/**/*.html
    python3 scripts/faq_mirror.py <URL>          # fetch and check one page
    python3 scripts/faq_mirror.py <path.html>    # check a local file

Exit 0 = all checked pages pass, exit 1 = at least one mismatch.

Used as pre/post-deploy Gate 5 (Sprint 1, 2026-11-05). Link-text-faithful
flattening: block-closing tags become a space, inline tags vanish, so
`Design</a>.` flattens to `Design.` (not `Design .`).
"""
import json
import re
import sys
import urllib.request
from html import unescape
from pathlib import Path

BLOCK_CLOSE = re.compile(
    r"</(p|div|h[1-6]|li|tr|td|th|section|aside|ul|ol|figcaption|dt|dd)>",
    re.I,
)
TAG = re.compile(r"<[^>]+>")
SCRIPT = re.compile(r"<script[^>]*>.*?</script>", re.S | re.I)
STYLE = re.compile(r"<style[^>]*>.*?</style>", re.S | re.I)
JSONLD = re.compile(r"<script[^>]*application/ld\+json[^>]*>(.*?)</script>", re.S | re.I)
MD_Q = re.compile(
    r'<div itemscope itemprop="mainEntity" itemtype="https://schema.org/Question"'
    r'[^>]*>\s*<h3 itemprop="name">(.*?)</h3>',
    re.S,
)


def flatten(text: str) -> str:
    """Visible text of a fragment: block closes -> space, tags dropped."""
    text = BLOCK_CLOSE.sub(" ", text)
    text = TAG.sub("", text)
    return re.sub(r"\s+", " ", unescape(text)).strip()


def visible_text(html: str) -> str:
    """Full-page visible text (scripts/styles removed, flattened)."""
    text = SCRIPT.sub(" ", html)
    text = STYLE.sub(" ", text)
    return re.sub(r"\s+", " ", flatten(text))


def faq_jsonld(html: str):
    """Return the first FAQPage JSON-LD dict, or None."""
    for block in JSONLD.findall(html):
        try:
            data = json.loads(block.strip())
        except (ValueError, TypeError):
            continue
        items = data if isinstance(data, list) else [data]
        for item in items:
            if isinstance(item, dict) and item.get("@type") == "FAQPage":
                return item
    return None


def check(html: str) -> list:
    """Return a list of mismatch strings (empty = pass)."""
    fails = []
    faq = faq_jsonld(html)
    if faq is None:
        return ["no FAQPage JSON-LD found"]

    questions = faq.get("mainEntity", [])
    if not questions:
        return ["FAQPage JSON-LD has no mainEntity"]

    vis = visible_text(html)
    for q in questions:
        name = flatten(q.get("name", ""))
        answer = flatten(q.get("acceptedAnswer", {}).get("text", ""))
        if name.lower() not in vis.lower():
            fails.append(f"Q-miss: {name[:80]}")
        if answer.lower() not in vis.lower():
            fails.append(f"A-miss: {name[:60]}")

    # microdata FAQPage (when present) must equal JSON-LD, in order
    md_names = [flatten(x) for x in MD_Q.findall(html)]
    if md_names:
        json_names = [flatten(q.get("name", "")) for q in questions]
        if md_names != json_names:
            fails.append(
                f"microdata != JSON-LD ({len(md_names)} vs {len(json_names)} items)"
            )
    return fails


def load(target: str) -> str:
    if target.startswith(("http://", "https://")):
        req = urllib.request.Request(
            target, headers={"User-Agent": "Mozilla/5.0 (faq_mirror gate)"}
        )
        with urllib.request.urlopen(req, timeout=30) as resp:
            return resp.read().decode("utf-8", "ignore")
    return Path(target).read_text(encoding="utf-8", errors="ignore")


def main(argv: list) -> int:
    if len(argv) > 1:
        target = argv[1]
        try:
            html = load(target)
        except Exception as exc:  # network/IO failure = gate failure, loudly
            print(f"ERROR loading {target}: {exc}")
            return 1
        fails = check(html)
        if fails:
            print(f"FAIL {target}")
            for f in fails:
                print(f"  {f}")
            return 1
        n = len(faq_jsonld(html)["mainEntity"])
        print(f"PASS {target} — {n}/{n} Q+A character-exact (visible <-> JSON-LD <-> microdata)")
        return 0

    # no args: site-wide scan of the static frontend.
    # Scope = pages with a parseable FAQPage JSON-LD (the plan's "209").
    # Pages that merely *mention* FAQPage (e.g. glossary microdata-only
    # markup) carry no JSON-LD for this gate to compare — skipped.
    q_miss, a_miss, md_mismatch = set(), set(), set()
    checked = 0
    for page in sorted(Path("frontend").rglob("*.html")):
        html = page.read_text(encoding="utf-8", errors="ignore")
        if "FAQPage" not in html:
            continue
        if faq_jsonld(html) is None:
            continue
        checked += 1
        for f in check(html):
            if f.startswith("Q-miss"):
                q_miss.add(str(page))
            elif f.startswith("A-miss"):
                a_miss.add(str(page))
            elif f.startswith("microdata"):
                md_mismatch.add(str(page))

    union = q_miss | a_miss | md_mismatch
    for page in sorted(union):
        print(f"FAIL {page}")
        for f in check(Path(page).read_text(encoding="utf-8", errors="ignore")):
            print(f"  {f}")
    print(f"\n{checked} FAQPage JSON-LD pages scanned")
    print(f"  Q-miss (schema Q absent from visible):   {len(q_miss)}  <- ticket scope")
    print(f"  A-miss (schema answer not character-exact): {len(a_miss)}")
    print(f"  microdata != JSON-LD item count/order):  {len(md_mismatch)}")
    print(f"  union of violating pages:                {len(union)}")
    return 1 if union else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
