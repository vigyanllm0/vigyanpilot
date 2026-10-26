# Pre-existing Issue Tickets — Week-3 SEO Scope Boundaries

Findings surfaced during Week-3 work. **Deliberately NOT bundled into the Week-3 commit.**
Each ticket independent; fix on its own branch with its own gates.

---

## TICKET-1 (CRITICAL) — `sync-frontend.sh` missing `uploads/*` guard on this branch

- **Severity:** P0 — can destroy production media
- **Evidence:** `git diff origin/main -- deploy/aws/sync-frontend.sh` = **13 deletions** (branch lacks
  origin/main's guard lines). `grep -c 'exclude "uploads/\*"'` on this branch = **0**.
  Bucket currently holds **8 CMS uploads** (`uploads/cms/2026/*/*.jpg`, the only copy — not in git).
- **Impact:** All 7 sync passes use `--delete`. Without the exclude, a full run on this branch
  can delete the 8 remote-only CMS images (the exact incident documented 2026-10-14).
- **Mitigation used this session:** surgical `aws s3 cp` of the 10 changed files, no `--delete`.
  Uploads verified 8/8 intact after deploy.
- **Fix:** restore origin/main's version (`git restore --source=origin/main --worktree -- deploy/aws/sync-frontend.sh`),
  never run the branch version until restored. Verify: `grep -c 'exclude "uploads/\*"'` = 7.
- **Branch hygiene:** rebase/merge origin/main into `wip/mega-menu` to end the drift.

## TICKET-2 — Committed `sitemap.xml` stale vs disk

- 68 pages on disk absent from committed sitemap; 161 priority drift; 24 entries would be removed.
- **Do not** "just run" `generate_sitemap.py` — a full regen sweeps that drift into one unreviewable diff.
- Fix = deliberate regen pass: diff old vs new, review, commit alone.

## TICKET-3 — `robots.txt` template reconciliation

- Committed file carries legacy `Disallow:` block the generator template lacks
  (`/features/`, `/about/`, `/hub/`, `/nav`, `/api.vigyanllm.in/`). File has drifted from template.
- Decision needed: legacy rules stay (then template updated) or go (then regen).
- This session only synced the count lines (445→418, glossary 355→328); rules untouched.

## TICKET-4 — `bake_partials.py --check` fails repo-wide at HEAD

- Most branch pages close `</main>` **inside** the stale baked block; origin/main canonical structure
  closes `</main>` before `#vl-footer`. `--check` fails across the repo at HEAD.
- The 8 Week-3 pages follow origin/main canonical structure.
- Fix = repo-wide rebake + structure review (own branch, own deploy window).

## TICKET-5 — Baker edge cases (2 files)

- `frontend/clustal-vs-tcoffee.html` — no empty header placeholder → baker cannot inject.
- `frontend/ncbi-primer-blast-vs-vigyanllm.html` — no empty footer placeholder → baker cannot inject.
- Both appear to be Week-2 hand-authored pages missing the partial slots.

## TICKET-6 — GSC URL Inspection batch (operational, not code)

- Request Indexing for the 8 URLs, 10/day limit → 1 batch, Day 2–3.
- Track in `docs/seo-week3/gsc-submission-workflow.md`.

## TICKET-7 — `_redirects` file is inert on this stack (documentation only, no fix needed)

- `frontend/_redirects` follows the Netlify convention but **S3/CloudFront never reads it**.
- Live redirect behavior (www→non-www, `.html`→clean URL, `/r/` referral, 11 legacy paths)
  is implemented in the CloudFront Function `deploy/aws/cloudfront-functions/viewer-request.js`.
- Verified live 2026-10-26: `.html → 301 clean` works for `/blog/`, `/gene-prefers/`,
  `/features/`, `/hub/` — via the Function, not the file.
- **Action taken:** header comment added to `_redirects` (2026-10-26) so future maintainers
  don't waste time editing it. No code change needed; file kept for parity/documentation.
