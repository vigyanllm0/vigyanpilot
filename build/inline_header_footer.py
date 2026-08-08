#!/usr/bin/env python3
"""
One-time canonical header/footer inliner.

Source of truth: frontend/header.html and frontend/footer.html (extracted from
frontend/index.html). This script replaces every public page's existing
<header>...</header> and <footer>...</footer> blocks with the canonical copy,
leaving each page's <main> body, inline scripts, and all button/nav code in the
body region exactly as-is (no nav-bar changes / no extra buttons inside any
page body).

Excluded (separate admin trust boundary, per AGENTS.md — own auth at :8001):
  - frontend/cms-admin.html
  - frontend/cms-editor.html
"""
import re, glob, os, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FRONTEND = os.path.join(ROOT, "frontend")
HEADER = os.path.join(FRONTEND, "header.html")
FOOTER = os.path.join(FRONTEND, "footer.html")
EXCLUDE = {"cms-admin.html", "cms-editor.html"}

HEADER_INNER = open(HEADER).read()
FOOTER_INNER = open(FOOTER).read()

HDR_RE = re.compile(r"<header>.*?</header>", re.S)
FTR_RE = re.compile(r"<footer>.*?</footer>", re.S)

changed = 0
skipped = 0
missing = []
for path in sorted(glob.glob(os.path.join(FRONTEND, "**", "*.html"), recursive=True)):
    name = os.path.basename(path)
    if name in EXCLUDE:
        skipped += 1
        continue
    s = open(path).read()
    had_hdr = bool(HDR_RE.search(s))
    had_ftr = bool(FTR_RE.search(s))

    new = s
    if had_hdr:
        new = HDR_RE.sub(lambda m: "<header>\n" + HEADER_INNER + "\n</header>", new, count=1)
    else:
        # page lacks a header (e.g. checkout.html) — nothing to replace; do not inject
        pass
    if had_ftr:
        new = FTR_RE.sub(lambda m: "<footer>\n" + FOOTER_INNER + "\n</footer>", new, count=1)
    else:
        pass

    if new != s:
        open(path, "w").write(new)
        changed += 1
    else:
        skipped += 1

    if not had_hdr and not had_ftr:
        missing.append(name)

print(f"Pages inlined with canonical header/footer: {changed}")
print(f"Pages skipped (already identical, or no header/footer present): {skipped}")
if missing:
    print(f"Pages with NO header/footer block (left untouched): {missing}")
if skipped == 0 and not missing:
    print("\nAll public pages now share one header/footer scheme.")
