# TICKET-AMP-301 — `/amplicon-size-calculator` 404 with residual GSC impressions → 301

- **Priority:** P3 (cleanup, not blocking)
- **Owner:** dev team
- **Raised:** 2026-11-05 (QA of execution plan v3, P7)
- **Gate:** no FAQ/schema changes involved; `scripts/rules_lint.py` 0 errors; commit/push/deploy
  only on explicit owner go.

## Evidence

- **Live:** `https://www.vigyanllm.in/amplicon-size-calculator` → **404** (verified 2026-11-05).
- **Never existed in git:** `git log --all -- frontend/amplicon-size-calculator.html` → empty;
  `find frontend -iname '*amplicon*'` → only glossary/blog assets. The URL was never a real page.
- **GSC residual:** owner reports **39 impressions @ avg position 3.18** on this URL — real
  queries are being shown a 404 (classic query-level demand hitting a nonexistent path; the
  "19–30% CTR" figure v3 cited came from this query cluster, not from a page we own).
- **v3 Finding N4** wrongly listed it as a "winning calculator" — corrected in the QA-patched
  plan (§2 callout).

## Decision (per ticket rule)

**Impressions exist (39 @ pos 3.18) → 301 redirect to the canonical calculator.**

Target: **`/pcr-product-calculator`** (exists, 203 clicks / 6,804 impr / 3.0% CTR / pos 5.2 —
the page that actually owns amplicon-size intent; it even ranks #4 for
"pcr product size calculator" @ 20.3% CTR in the baseline query table).

## Implementation

1. Add to the CloudFront Function redirect table in
   `deploy/aws/cloudfront-functions/viewer-request.js` (the established mechanism — same table
   as the 11 redirects shipped in v15/v17):
   ```
   /amplicon-size-calculator → /pcr-product-calculator   (301)
   ```
   Follow the existing redirect-entry format exactly; bump the file header + Config Comment
   version in lockstep (v17 → v18).
2. Publish: `update-function` (Comment+Runtime only, no Name) → `publish-function --if-match
   <dev-etag>` → live ~6 s. Byte-compare LIVE function to repo.
3. Verify live with a **no-redirect** client (urllib follows 301s and hides Location):
   `curl -s -o /dev/null -w '%{http_code} %{redirect_url}' --max-redirs 0
   https://www.vigyanllm.in/amplicon-size-calculator` → `301 …/pcr-product-calculator`
   then target → 200.
4. GSC follow-up (owner): URL Inspection on the old URL → confirm redirect picked up;
   the 39 impressions should transfer to `/pcr-product-calculator` within a crawl cycle.
   No Change-of-Address needed (single URL).
5. Also check: does anything in-repo link to `/amplicon-size-calculator`? (2026-11-05 grep:
   no frontend hits — re-verify at fix time.)

## Acceptance criteria

- [ ] Old URL → **301** → `/pcr-product-calculator` (200, 0 hops after redirect)
- [ ] LIVE CloudFront Function byte-identical to repo; version comment bumped
- [ ] Existing 11 redirects + `/r/` referral path still pass the local harness (`/tmp/cf_test3.js`
      45/45 or current equivalent) before publish
- [ ] `scripts/rules_lint.py` 0 errors
- [ ] GSC: old URL shows "Page with redirect" instead of 404 after next crawl

## Out of scope

- Building an actual amplicon-size calculator page (v3 P7: the "winner" never existed; if GSC
  query demand justifies it, revisit in Sprint 3 as a *build* decision with the
  `/pcr-product-calculator` cannibalization check first)
