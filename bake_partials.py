#!/usr/bin/env python3
"""Bake /partials/header.html and /partials/footer.html into page markup.

Pages that use <script src="/includes.js"> fetch the two partials client-side
at runtime. That costs a render-blocking fetch chain per page view and hides
nav content from crawlers until JS runs (GSC Tier 2: "server-side header/
footer — kill the includes.js client-side partial fetch").

This script injects the partial HTML directly into each page's
<div id="vl-header"> / <div id="vl-footer"> placeholder, wrapped in
comment markers so the bake can be re-run after any partial edit:

    python3 bake_partials.py            # bake (idempotent)
    python3 bake_partials.py --check    # report only, exit 1 if out of date

The includes.js <script> tag is intentionally KEPT: it runs accessibility
wiring (dropdown ARIA, hamburger aria-expanded) and dispatches
'vl-includes-loaded'. Since the placeholders are already filled, its fetch is
skipped (loadPartial checks hasChildNodes).

After editing partials/header.html or partials/footer.html, re-run this
script, then commit the partial AND all re-baked pages together.
"""
from __future__ import annotations

import glob
import re
import sys

START = {
    "vl-header": "<!--vl-header-bake-start-->",
    "vl-footer": "<!--vl-footer-bake-start-->",
}
END = {
    "vl-header": "<!--vl-header-bake-end-->",
    "vl-footer": "<!--vl-footer-bake-end-->",
}


def load_partials() -> dict[str, str]:
    out = {}
    for pid in ("vl-header", "vl-footer"):
        path = f"frontend/partials/{pid.split('-', 1)[1]}.html"
        with open(path, encoding="utf-8") as fh:
            out[pid] = fh.read().strip()
        if not out[pid]:
            raise SystemExit(f"partial is empty: {path}")
        if START[pid] in out[pid] or END[pid] in out[pid]:
            raise SystemExit(f"partial contains bake markers: {path}")
    return out


def bake(content: str, pid: str, partial: str) -> str | None:
    """Return updated content, or None when no change is needed."""
    start, end = START[pid], END[pid]
    block = f"{start}{partial}{end}"

    if start in content:
        rx = re.compile(re.escape(start) + r".*?" + re.escape(end), re.S)
        if rx.sub(lambda m: block, content, count=1) == content:
            return None
        return rx.sub(lambda m: block, content, count=1)

    empty = f'<div id="{pid}"></div>'
    if empty in content:
        return content.replace(empty, f'<div id="{pid}">{block}</div>', 1)

    raise SystemExit(f'no empty <div id="{pid}"> placeholder found')


def main() -> int:
    check_only = "--check" in sys.argv
    partials = load_partials()
    pages = [
        f
        for f in glob.glob("frontend/**/*.html", recursive=True)
        if "/partials/" not in f and "/api/" not in f
    ]

    baked = skipped = stale = 0
    missing: list[str] = []
    for page in sorted(pages):
        with open(page, encoding="utf-8", errors="surrogateescape") as fh:
            original = fh.read()

        uses_includes = "/includes.js" in original
        has_placeholder = 'id="vl-header">' in original or 'id="vl-footer">' in original
        if not (uses_includes or has_placeholder):
            continue
        if not has_placeholder:
            continue  # includes.js on a page without placeholders: leave alone

        updated = original
        try:
            for pid, partial in partials.items():
                if f'id="{pid}">' not in updated:
                    continue
                nxt = bake(updated, pid, partial)
                if nxt is not None:
                    updated = nxt
        except SystemExit as exc:
            missing.append(f"{page}: {exc}")
            continue

        if updated == original:
            skipped += 1
            continue
        if check_only:
            stale += 1
            continue
        with open(page, "w", encoding="utf-8", errors="surrogateescape") as fh:
            fh.write(updated)
        baked += 1

    for m in missing:
        print(f"ERROR {m}")
    if check_only:
        print(f"check: {stale} stale, {skipped} up to date")
        return 1 if (stale or missing) else 0
    print(f"baked: {baked}, already up to date: {skipped}, errors: {len(missing)}")
    return 1 if missing else 0


if __name__ == "__main__":
    sys.exit(main())
