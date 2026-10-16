#!/usr/bin/env python3
"""Per-pair link evidence gate for work orders (standing rule, 2026-10-16).

A work order that claims "N/N donor links live" must produce a map of
(donor, phrase, target) triples; this script greps each donor file for the
target href AND verifies the anchor phrase is the text of that link — then
prints per-pair PASS/FAIL and exits non-zero on any failure.

Why sampled verification failed (Batch #6-9): a donor page that itself 301'd
made link-following checks land elsewhere and see nothing; sampling missed the
two zero-link targets entirely. Per-pair, file-side evidence can't be fooled
by redirects or render order.

Usage:
    python3 scripts/verify_workorder_links.py MAP.json [--frontend frontend/]

Map format (JSON list):
    [{"donor": "blog/slug-or-path", "phrase": "anchor text", "target": "glossary/slug"}, ...]
    - donor: path relative to frontend/, WITH or WITHOUT .html
    - target: site path WITHOUT leading slash; href /{target} or /{target}.html both match
    - phrase: optional; when present, must occur inside the anchor element's text
"""
import argparse
import html
import json
import re
import sys
from pathlib import Path

ANCHOR_RE = re.compile(r"<a\b[^>]*href=[\"']([^\"']+)[\"'][^>]*>(.*?)</a>", re.I | re.S)
TAG_RE = re.compile(r"<[^>]+>")


def _anchor_text(fragment: str) -> str:
    """Visible text of an anchor fragment (strips nested tags, collapses ws)."""
    return " ".join(html.unescape(TAG_RE.sub(" ", fragment)).split())


def resolve_donor(frontend: Path, donor: str) -> Path | None:
    """donor 'blog/x' or 'index' or 'blog/x.html' -> frontend file."""
    rel = donor[1:] if donor.startswith("/") else donor
    if not rel.endswith(".html"):
        rel += ".html"
    p = frontend / rel
    return p if p.is_file() else None


def check_pair(frontend: Path, pair: dict) -> tuple[bool, str]:
    donor = pair.get("donor", "")
    target = pair.get("target", "").strip("/")
    phrase = (pair.get("phrase") or "").strip()
    if not donor or not target:
        return False, "map entry missing donor/target"
    f = resolve_donor(frontend, donor)
    if f is None:
        return False, f"donor file not found: {donor}.html"
    src = f.read_text(encoding="utf-8", errors="ignore")
    want = {f"/{target}", f"/{target}.html"}

    def _norm(href: str) -> str:
        """Relative or absolute-origin href -> path (hub/breadcrumbs use absolute URLs)."""
        p = href.split("?")[0].split("#")[0]
        for origin in ("https://www.vigyanllm.in", "https://vigyanllm.in"):
            if p.startswith(origin):
                p = p[len(origin):] or "/"
        return p

    hits = [(h, frag) for h, frag in ANCHOR_RE.findall(src) if _norm(h) in want]
    if not hits:
        return False, f"no <a href> to /{target} in {donor}.html"
    if not phrase:
        return True, f"{len(hits)} link(s) to /{target} (no phrase asserted)"
    for h, frag in hits:
        at = _anchor_text(frag)
        if phrase.lower() in at.lower():
            return True, f'href="{h}" text="{at[:70]}"'
    seen = "; ".join(_anchor_text(f)[:40] for _, f in hits)
    return False, f'link to /{target} exists but anchor is not "{phrase}" (got: {seen})'


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("map", help="JSON map of donor/phrase/target triples")
    ap.add_argument("--frontend", default="frontend/", help="frontend root (default: frontend/)")
    args = ap.parse_args()

    pairs = json.loads(Path(args.map).read_text(encoding="utf-8"))
    if not isinstance(pairs, list) or not pairs:
        print(f"FAIL: {args.map} is not a non-empty JSON list")
        return 1
    frontend = Path(args.frontend)
    if not frontend.is_dir():
        print(f"FAIL: frontend root not found: {frontend}")
        return 1

    failures = 0
    for i, pair in enumerate(pairs, 1):
        ok, detail = check_pair(frontend, pair)
        mark = "PASS" if ok else "FAIL"
        print(f"  [{mark}] {i:2}/{len(pairs)} {pair.get('donor','?')} -> "
              f"/{pair.get('target','?')} :: {detail}")
        if not ok:
            failures += 1

    total = len(pairs)
    verdict = "OK" if failures == 0 else f"{failures} FAILED"
    print(f"\n{total - failures}/{total} pairs verified ({verdict}) — {args.map}")
    return 0 if failures == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
