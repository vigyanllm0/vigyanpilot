# Mega-Menu Snapshot — Evidence Pack (Read-Only, No Merge)

**Commit:** `41c64448` — "preserve: mega-menu nav WIP snapshot (534 files + navprev assets + sync script"
**Branch:** `wip/mega-menu` (Desktop worktree)
**Status:** HELD — awaiting founder keep/kill/defer ruling

## What It Contains

- **580 files changed**, 116,351 insertions, 24,468 deletions
- **534 modified files** (existing pages with nav/header changes)
- **New files:** `sync_inline_header.py` (134 lines — batch header sync script), `navprev/` assets
- **Modified:** `generate_sitemap.py` (+10 lines), `frontend/validation.html` (+238 lines), `frontend/verify-email.html` (+240 lines)

## What Changed (Diff Summary)

The commit appears to be a **site-wide navigation restructure**:
- Inline header partials synced across 534 pages
- Mega-menu dropdown added to nav
- `sync_inline_header.py` script for batch-updating headers
- Nav terms changed (academic-partnership, etc.)

## Risk Assessment

- **Scope:** Massive — touches 534 of 537 HTML pages
- **Authorization:** Never explicitly authorized (per AGENTS.md: "it was never authorized work; it needs its own review")
- **Conflict risk:** Very high — any merge to main would conflict with every subsequent commit
- **Reversibility:** Committed (safe from disk failure), but NOT pushed

## Recommendation

**Defer.** The navigation restructure may have value, but:
1. It was never scoped or authorized
2. The conflict surface is enormous (534 files)
3. The repo has since moved forward significantly (pharma suite, qPCR, pricing, etc.)
4. A targeted nav improvement would be better than a 534-file blast

If the founder wants a mega-menu, it should be:
- Built on a clean branch off current main
- Scoped to nav partials only (not 534 file edits)
- Using the partial/bake system already on main (not inline header sync)

## Files for Review

- `sync_inline_header.py` — the batch header sync script
- `frontend/navprev/` — nav snapshot assets
- Diff: `git diff 41c64448~1..41c64448 --stat` (580 files)