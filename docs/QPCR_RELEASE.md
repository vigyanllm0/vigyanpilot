# qPCR Analyzer — Release Mechanics

**Status:** HELD (founder demo + methods-wording sign-off required)
**Trigger:** Founder says "go" after demo + methods sign-off

## Pre-Flight Checklist

- [ ] Headless 9/9 desktop + mobile (all tabs, 0 console errors)
- [ ] rules_lint 0 err
- [ ] FAQ mirror 0/0
- [ ] JSON-LD parses (SoftwareApplication + FAQPage + BreadcrumbList)
- [ ] ruff clean (tests/qpcr_mirror.py)
- [ ] Full pytest suite green
- [ ] PSI ≥90 (mobile + desktop) — first post-sync check
- [ ] 3 demo files ready (SYBR, TaqMan, problem run)
- [ ] Methods wording approved by founder
- [ ] Sitemap count: 414 → 415 (pharma-held URLs unchanged)

## Release Command (10 minutes)

```bash
# 1. Add to sitemap (already in generate_sitemap.py PRIORITY_MAP? check)
# qpcr-analyzer.html should be in PRIORITY_MAP with priority 0.90

# 2. Regenerate sitemap
python3 generate_sitemap.py
# Verify: count = 415, pharma URLs still held (HELD_FOR_SIGNOFF non-empty)

# 3. Sync frontend
bash deploy/aws/sync-frontend.sh
# qpcr-analyzer.html + qpcr/ directory

# 4. Invalidate CloudFront
aws cloudfront create-invalidation --distribution-id E394TCXPIP8P6R --paths "/qpcr-analyzer" "/qpcr-analyzer.html" "/qpcr/*"

# 5. IndexNow
curl -X POST https://api.indexnow.org/indexnow -H "Content-Type: application/json" \
  -d '{"host":"www.vigyanllm.in","key":"<INDEXNOW_KEY>","urlList":["https://www.vigyanllm.in/qpcr-analyzer"]}'

# 6. Request Indexing (Google Search Console)
# Manual: GSC → URL Inspection → Request Indexing for /qpcr-analyzer
```

## Rollback

```bash
git revert <release-commit>
python3 generate_sitemap.py
bash deploy/aws/sync-frontend.sh
# invalidate same paths
```

## Founder Touchpoints (the ONLY things between this and launch)

1. **Demo** (5 min walkthrough): upload → views → My Views save → URL share → methods copy → PDF export
2. **Methods wording sign-off**: approve the exact sentence templates with placeholders
3. **"Go"**: flip the switch

## Demo Files

1. **SYBR run** (good): standard curve + melt + expression — shows the happy path
2. **TaqMan multiplex**: multi-channel, multi-target — shows channel tabs + plate view
3. **Problem run** (bad efficiency, NTC flags, high replicate SD) — shows the QC system selling itself