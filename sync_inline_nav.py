#!/usr/bin/env python3
"""Sync the partial header's nav bar into pages that carry an inline copy.

bake_partials.py rewrites whole partials on the pages given a
<div id="vl-header"> / <div id="vl-footer"> placeholder. The remaining
pages predate the partial system and hold a verbatim copy of the nav, so
an edit to partials/header.html lands on the baked pages and silently
misses the inline ones (nav content then differs page to page — the drift
that made the mega-menu WIP touch 540 files).

This script updates the two nav pieces that live *inside* every inline
copy:

  1. the desktop nav-links block — bounded by '<div class="nav-links">'
     and the '<div class="nav-right">' that always follows it, so whatever
     markup a page holds is replaced by the partial's current markup;
  2. the mobile-menu "Pharma & Lab" mm-group — inserted right after the
     Services mm-group when the page's mobile menu does not carry it yet.

    python3 sync_inline_nav.py            # sync (idempotent)
    python3 sync_inline_nav.py --check    # report only, exit 1 if stale

After editing partials/header.html run:

    python3 bake_partials.py && python3 sync_inline_nav.py

Scope: every frontend/**/*.html except /partials/ and /api/. Pages with
no '<div class="nav-links">' (cms-login, bare qpcr pages, header/footer
source files) are skipped untouched.
"""
from __future__ import annotations

import glob
import sys

PARTIAL = "frontend/partials/header.html"
NAV_OPEN = '<div class="nav-links">'
NAV_CLOSE = '<div class="nav-right">'
MM_SERVICES = '<div class="mm-hdr">Services</div>'
MM_PHARMA_HDR = '<div class="mm-hdr">Pharma &amp; Lab</div>'
MM_GROUP_OPEN = '<div class="mm-group">'
SERVICES_LINK = "Customised Pipeline"
# a real nav-links block is ~2.5–4 KB; anything far past that means the
# page's markup does not follow the assumed shape — leave it alone loudly.
MAX_BLOCK = 6000


def load_partial() -> str:
    with open(PARTIAL, encoding="utf-8") as fh:
        return fh.read()


def nav_block(partial: str) -> str:
    i = partial.index(NAV_OPEN)
    j = partial.index(NAV_CLOSE, i)
    return partial[i:j]


def pharma_mm_group(partial: str) -> str:
    """The partial's own mobile 'Pharma & Lab' mm-group, minus indentation."""
    hdr = partial.index(MM_PHARMA_HDR)
    start = partial.rindex(MM_GROUP_OPEN, 0, hdr)
    link = partial.index("Pharma Calculators</a>", hdr)
    end = partial.index("</div>", link) + len("</div>")
    return partial[start:end]


def sync_page(text: str, block: str, group: str) -> tuple[str, str, str]:
    """Return (updated_text, note, warning); note == '' when unchanged."""
    note = ""
    warning = ""

    # 1. desktop nav-links block → the partial's current block
    i = text.find(NAV_OPEN)
    if i != -1:
        j = text.find(NAV_CLOSE, i)
        if j == -1:
            warning = "nav-links without nav-right"
        elif j - i > MAX_BLOCK:
            warning = f"nav-links block too large ({j - i} B) — not synced"
        elif text[i:j] != block:
            text = text[:i] + block + text[j:]
            note = "nav"

    # 2. mobile Pharma & Lab mm-group right after the Services mm-group
    k = text.find(MM_SERVICES)
    if k != -1 and MM_PHARMA_HDR not in text:
        p = text.find(SERVICES_LINK, k)
        if p == -1:
            warning = (warning + "; " if warning else "") + \
                "Services mm-group without Customised Pipeline link"
        else:
            e = text.find("</div>", p)
            if e != -1:
                e += len("</div>")
                text = text[:e] + "\n  " + group + text[e:]
                note = (note + ",mobile") if note else "mobile"
    return text, note, warning


def main() -> int:
    check = "--check" in sys.argv
    partial = load_partial()
    block, group = nav_block(partial), pharma_mm_group(partial)

    changed: list[tuple[str, str]] = []
    warnings: list[tuple[str, str]] = []
    no_nav: list[str] = []
    written = 0

    pages = sorted(
        f for f in glob.glob("frontend/**/*.html", recursive=True)
        if "/partials/" not in f and "/api/" not in f
    )
    for path in pages:
        with open(path, encoding="utf-8", errors="surrogateescape") as fh:
            original = fh.read()
        if NAV_OPEN not in original:
            no_nav.append(path)
            continue
        updated, note, warning = sync_page(original, block, group)
        if warning:
            warnings.append((path, warning))
        if updated == original:
            continue
        changed.append((path, note))
        if not check:
            with open(path, "w", encoding="utf-8", errors="surrogateescape") as fh:
                fh.write(updated)
            written += 1

    nav_n = sum(1 for _, n in changed if "nav" in n.split(","))
    mob_n = sum(1 for _, n in changed if "mobile" in n.split(","))
    if check:
        print(f"check: {len(changed)} stale"
              + (f", {len(warnings)} warnings" if warnings else ""))
        for path, note in changed[:20]:
            print(f"  {path} ({note})")
        return 1 if changed else 0

    print(f"inline nav: {len(changed)} updated "
          f"({nav_n} desktop, {mob_n} mobile, {written} written), "
          f"{len(no_nav)} skipped without nav-links, "
          f"{len(warnings)} warnings")
    for path, warning in warnings[:20]:
        print(f"  WARNING {path}: {warning}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
