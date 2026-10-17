# Mega-Menu WIP — Adjudication Report (Phase 0.4)

**Date:** 2026-10-18 · **Status:** Recommendation — no merge performed, branch preserved
**Inputs:** `docs/MEGA_MENU_EVIDENCE.md` (founder's evidence pack), fresh diff measurement vs `origin/main`, headless screenshots of the Desktop `:5199` preview

---

## Verdict

**KILL the merge path — KEEP the branch as a design archive.**

Same conclusion as the founder's evidence pack (defer): `wip/mega-menu` must never be merged into `main`. It has never been authorized, never CI'd, and merging it now would fight a ~549-file conflict war over the exact nav surface `main` has already resolved a different and already-shipped way. The branch stays pushed and untouched; if the mega-menu UX is wanted later, rebuild it **scoped** off current `main` (recipe below), copying salvageable assets from this branch — do not revive this branch.

---

## Snapshot (measured 2026-10-18)

| Fact | Value |
|---|---|
| Branch | `wip/mega-menu` @ `41c64448` — "preserve: mega-menu nav WIP snapshot (534 files + navprev assets + sync script)" |
| Provenance | 1 commit on merge-base `4dffb67f` (2026-10-14); `origin/main` is **69 commits** ahead (HEAD `40b42b93`) |
| Diff vs base | **580 files changed, +116,351 / −24,468** |
| Remote status | **Pushed to `origin` during Phase 0** (was local-only on the Desktop machine = single-machine risk). Desktop checkout untouched — its HEAD is the branch, working tree clean but for `bandit-report.json` (never-commit list). |
| CI / deploys | None, ever. |

Remote branch inventory after Phase 0: `main`, `feature/pharma-suite`, `feature/qpcr-analyzer`, `wip/mega-menu`.

---

## Why it cannot merge

1. **Overlap math.** Since the merge-base, **549 files were changed by both sides** (main-since-base vs wip-since-base). **544 of the 548 files** touched by the just-merged nav port (`4ae0cd63`, PR #1) also appear in the WIP diff. The WIP's whole purpose — rewriting site nav — is the same surface the sanctioned port already shipped via `frontend/partials/header.html` + `sync_inline_nav.py` (bake 240 / sync 303, idempotent).
2. **Mutually exclusive designs.** The WIP is a mega-menu: **68 `dm-*` markers** in its header partial, five category rows with tool counts (Primer & PCR 8 / Sequence Analysis 6 / Genome Engineering 3 / Structural Biology 7 / Pharma & Lab 1) plus hover preview cards. `main` is flat drop-wraps: **0 `dm-*`**, a top-level **`Pharma & Lab ▾`** category (Antibiotic Stock Calculator + Pharma Calculators), footer link "Antibiotic Stocks" (`footer.html:28`). Main's design is merged, matches the staged-release nav policy (flagship + hub now; each stage adds its tools as they ship), and is the ratified shape.
3. **Stale SEO surfaces (forbidden files).** The WIP regenerated `sitemap.xml` at **445 `<loc>`** — a pre-2026-10-15 state that would resurrect the 21 noindexed URLs — and `robots.txt` (count comment 445, dated 2026-10-17). Committed `main` sits at **424** (held), live at **414**. Merging = regenerating sitemap/robots outside a release and clobbering `HELD_FOR_SIGNOFF`, which is explicitly prohibited.
4. **Superseded pharma drafts.** The WIP's `frontend/antibiotic-stock-calculator.html` and `frontend/pharma-calculators.html` differ from `main` by **+386/−114** (`pharma-calc.js` is byte-identical) — i.e. pre-merge drafts of the founder-reviewed suite (`517196bc`). `main` is canonical; the WIP versions must never ship.
5. **Mechanism superseded.** The WIP's `sync_inline_header.py` (134 lines, header-only) is superseded by the committed `sync_inline_nav.py` (bounded nav-links replace + idempotent mobile mm-group insert + `--check`), proven in Phase 0.3.

---

## What is worth keeping (salvage list)

- **The design itself** — category rows with tool counts, hover preview flyout cards with tool screenshots. Source markup: the branch's `frontend/partials/header.html`; visuals: screenshots below.
- **30 hover-preview images** — `frontend/assets/navprev/*.webp`, 616K, **committed on the branch** (verified: 30/30 tracked via `git cat-file`).
  *Correction to an earlier probe:* a previous check reported these assets "untracked, Desktop-only, would 404 on a fresh clone" — that was a **wrong-path false positive** (`frontend/navprev/` instead of the actual `frontend/assets/navprev/`). The snapshot is self-contained.
- **Preview-loader idea** from `sync_inline_header.py` (lazy `data-src` insertion) — reusable if a rebuild happens.

**Rebuild recipe (only if the founder rules for the mega UX):** new branch off `origin/main` → edit **only** `frontend/partials/header.html` + `frontend/design-tokens.css` → copy `frontend/assets/navprev/` from this branch → run `bake_partials.py` + `sync_inline_nav.py` (+ `--check`). A small, reviewable diff — versus this 580-file snapshot.

---

## Screenshots (headless capture of Desktop `:5199`, 1440px)

| File | Shows |
|---|---|
| `assets/nav_closed.png` | Nav closed — standard homepage baseline. |
| `assets/nav_open.png` | Products mega panel open: five category rows (icons, labels, tool counts, chevrons) + two image preview cards at right. |
| `assets/nav_open_flyout.png` | Hover preview flyout: Antibiotic Stock Calculator card — tool screenshot, "Try the free tool", **View tool** button. |

---

## Evidence (reproducible commands)

```
git rev-list --count $(git merge-base origin/main wip/mega-menu)..origin/main   → 69
git diff --shortstat BASE..wip/mega-menu                                        → 580 files, +116351 −24468
comm -12 <(git diff --name-only BASE..origin/main) \
         <(git diff --name-only BASE..wip/mega-menu) | wc -l                    → 549 both-sides overlap
git show wip/mega-menu:frontend/sitemap.xml | grep -c '<loc>'                   → 445 (main committed: 424, live: 414)
git show origin/main:frontend/partials/header.html | grep -c 'dm-'               → 0   (wip: 68)
git show origin/main:frontend/partials/header.html | grep -c 'Pharma &amp; Lab ▾' → 1   (wip: 0)
git diff --shortstat origin/main wip/mega-menu -- frontend/antibiotic-stock-calculator.html \
                                                     frontend/pharma-calculators.html
                                                                                → 2 files, +386 −114
```

**Decision belongs to the founder.** Until then: branch preserved on `origin`, never merged, never deleted.
