#!/usr/bin/env python3
"""Sync the header's nav bar + preview loader into pages that carry an inline copy.

bake_partials.py only touches pages that were given a <div id="vl-header">
placeholder (229 of them). The remaining pages predate the partial and hold
their own verbatim copy of <header>...</header>, so an edit to
partials/header.html lands on 229 pages and silently misses 303.

This script closes that gap for the two pieces that live *inside* every copy:

  1. the nav-links block - bounded by '<div class="nav-links">' and the
     '<div class="nav-right">' that always follows it, so whatever markup a
     page holds is replaced by the partial's current markup;
  2. the preview loader <script> that follows '</nav>...</header>' - inserted
     when missing (the inline copies never had it, so their screenshot cards
     were empty boxes), replaced in place when a previous copy of it is there.

    python3 sync_inline_header.py            # sync (idempotent)
    python3 sync_inline_header.py --check    # report only, exit 1 if stale

After editing partials/header.html run:
    python3 bake_partials.py && python3 sync_inline_header.py
"""
from __future__ import annotations

import glob
import os
import sys

PARTIAL = "frontend/partials/header.html"
NAV_OPEN = '<div class="nav-links">'
NAV_CLOSE = '<div class="nav-right">'
HDR_TAILS = ("</nav>\n</header>", "</nav></header>")
# both this and the previous loader's comment, so older copies get replaced
LOADER_MARKS = (
    "Header previews: every tab carries a screenshot card",
    "Products menu: attach preview screenshots",
)


def _partial() -> str:
    with open(PARTIAL, encoding="utf-8") as fh:
        return fh.read()


def partial_nav_block(text: str | None = None) -> str:
    text = text if text is not None else _partial()
    i = text.index(NAV_OPEN)
    return text[i:text.index(NAV_CLOSE, i)]


def partial_loader(text: str | None = None) -> str:
    text = text if text is not None else _partial()
    i = text.index(HDR_TAILS[0])          # the partial always uses the split form
    j = text.index("<script>", i)
    k = text.index("</script>", j) + len("</script>")
    return text[j:k]


def page_paths() -> list[str]:
    return sorted(
        f for f in glob.glob("frontend/**/*.html", recursive=True)
        if os.sep + "partials" + os.sep not in f
    )


def sync(text: str, nav_block: str, loader: str) -> tuple[str, str]:
    """Return (updated_text, note). note == '' when nothing needed changing."""
    note = ""

    i = text.find(NAV_OPEN)
    if i != -1:
        j = text.find(NAV_CLOSE, i)
        if j != -1 and text[i:j] != nav_block:
            text = text[:i] + nav_block + text[j:]
            note = "nav"

    # find the header tail, then whatever follows it
    after = -1
    for tail in HDR_TAILS:
        k = text.find(tail)
        if k != -1:
            after = k + len(tail)
            break
    if after != -1:
        rest = text[after:]
        lead = rest[:len(rest) - len(rest.lstrip())]      # whitespace after </header>
        body = rest[len(lead):]
        if body.startswith("<script>"):
            end = body.find("</script>")
            if end != -1:
                script = body[:end + len("</script>")]
                if any(m in script for m in LOADER_MARKS):
                    if script != loader:                   # replace stale loader
                        text = text[:after] + "\n" + loader + body[end + len("</script>"):]
                        note = (note + ",loader") if note else "loader"
                # an unrelated script belongs to the page - leave it alone
        else:
            # inline copy: no loader at all, so its screenshot cards never load
            text = text[:after] + "\n" + loader + lead + body
            note = (note + ",loader") if note else "loader"
    return text, note


def main() -> int:
    check = "--check" in sys.argv
    partial = _partial()
    nav_block, loader = partial_nav_block(partial), partial_loader(partial)
    stale: list[str] = []
    written = 0
    for path in page_paths():
        with open(path, encoding="utf-8") as fh:
            original = fh.read()
        if NAV_OPEN not in original:
            continue
        updated, _note = sync(original, nav_block, loader)
        if updated != original:
            stale.append(path)
            if not check:
                with open(path, "w", encoding="utf-8") as fh:
                    fh.write(updated)
                written += 1
    label = "stale" if check else "updated"
    print(f"inline headers: {len(stale)} {label}"
          + ("" if check else f" ({written} written)"))
    if stale and check:
        for path in stale[:20]:
            print(f"  {path}")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
