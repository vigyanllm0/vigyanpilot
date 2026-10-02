#!/usr/bin/env python3
"""rules_lint.py — machine-checkable subset of rules.md (Human-First Part 1).

Run before any frontend change is considered done:

    python3 scripts/rules_lint.py            # errors fail (exit 1), warnings print
    python3 scripts/rules_lint.py --strict   # warnings also fail (final gates)

Checks (ERROR level):
  E1  every <script type="application/ld+json"> parses as JSON
  E2  no fabricated/unevidenced aggregateRating (CLM-001/002/023 in docs/CLAIMS_LEDGER.md)
  E3  no literal \\uXXXX escapes in visible HTML text (outside <script>) — SEO-02
  E4  no "22-step"/"22 validation steps" leftovers — engine ground truth is 24 (CLM-019)
  E5  every public page has at least one <h1> (SEO-03)
  E6  no public page links to the admin shells /cms-login, /admin-security (SEC-01)
  E7  no en-IN/en-US hreflang (only en + x-default; SEO-04 / D-09)

Checks (WARN level, promoted by TRUST-03 completion):
  W1  banned unqualified claims (audit-ready / lab-ready / air-gapped / zero external API /
      clinical-grade / "no data leaves") — counts tracked vs docs/CLAIMS_LEDGER.md

Scope: frontend/**/*.html excluding components (frontend/header.html, frontend/footer.html,
partials/, api/) and the two admin shells (cms-login.html, admin-security.html, which are
redirect targets under plan decision D-05 and intentionally have no public copy to police).
"""
from __future__ import annotations

import glob
import json
import re
import sys

FRONTEND = "frontend"
SHELLS = {f"{FRONTEND}/cms-login.html", f"{FRONTEND}/admin-security.html"}
COMPONENTS = {f"{FRONTEND}/header.html", f"{FRONTEND}/footer.html"}
# Admin-tool pages are allowed to reference the shells internally (they are not public nav)
ADMIN_UI = {f"{FRONTEND}/cms-admin.html", f"{FRONTEND}/cms-editor.html", f"{FRONTEND}/cms-test.html"}
BANNED_CLAIMS = [
    "audit-ready", "lab-ready", "air-gapped",
    "zero external api", "clinical-grade", "no data leaves",
]

def pages() -> list[str]:
    out = []
    for f in sorted(glob.glob(f"{FRONTEND}/**/*.html", recursive=True)):
        if "/partials/" in f or "/api/" in f:
            continue
        if f in COMPONENTS:
            continue
        out.append(f)
    return out

def strip_scripts(html: str) -> str:
    return re.sub(r"<script\b.*?</script>", "", html, flags=re.S | re.I)

def main() -> int:
    strict = "--strict" in sys.argv
    errors: list[str] = []
    warns: list[str] = []
    claim_hits = {c: [] for c in BANNED_CLAIMS}

    for f in pages():
        text = open(f, encoding="utf-8", errors="surrogateescape").read()
        is_shell = f in SHELLS

        # E1 — JSON-LD parses
        for i, m in enumerate(re.finditer(
                r'<script type="application/ld\+json"[^>]*>(.*?)</script>', text, re.S)):
            try:
                json.loads(m.group(1))
            except Exception as exc:
                errors.append(f"E1 {f}: JSON-LD block #{i+1} does not parse: {exc}")

        # E2 — no unevidenced aggregateRating
        if "aggregateRating" in text and not is_shell:
            errors.append(f"E2 {f}: aggregateRating present (see docs/CLAIMS_LEDGER.md CLM-001/002/023)")

        # E3 — literal \uXXXX in visible text
        visible = strip_scripts(text)
        for m in re.finditer(r"\\u[0-9a-fA-F]{4}", visible):
            errors.append(f"E3 {f}: literal unicode escape {m.group(0)} in visible HTML")
            break

        # E4 — 22-step leftovers anywhere (incl. JSON-LD)
        m = re.search(r"22[\s-]validation steps?|22-step", text, re.I)
        if m:
            errors.append(f"E4 {f}: '22-step' leftover {m.group(0)!r} — ground truth is 24 (CLM-019)")

        # E5 — H1 present
        if not is_shell and not re.search(r"<h1[\s>]", text):
            errors.append(f"E5 {f}: no <h1>")

        # E6 — admin-shell links (shells + admin tool pages excluded)
        if not (is_shell or f in ADMIN_UI):
            if re.search(r'href="/(?:cms-login|admin-security)"', text):
                errors.append(f"E6 {f}: links to admin shell (SEC-01)")

        # E7 — hreflang trim
        if re.search(r'hreflang="(?:en-IN|en-US)"', text):
            errors.append(f"E7 {f}: en-IN/en-US hreflang should be trimmed to en + x-default (SEO-04)")

        # W1 — banned claims (TRUST-03 backlog)
        low = text.lower()
        for c in BANNED_CLAIMS:
            n = low.count(c)
            if n:
                claim_hits[c].append(f"{f}×{n}")

    for c, files in claim_hits.items():
        if files:
            warns.append(f"W1 banned claim {c!r}: {len(files)} file(s) — {', '.join(files[:6])}"
                         + (" …" if len(files) > 6 else ""))

    for e in errors:
        print("ERROR", e)
    for w in warns:
        print("WARN ", w)

    print(f"\nrules_lint: {len(errors)} error(s), {len(warns)} warning group(s), {len(pages())} pages scanned")
    if errors:
        return 1
    if strict and warns:
        return 1
    return 0

if __name__ == "__main__":
    sys.exit(main())
