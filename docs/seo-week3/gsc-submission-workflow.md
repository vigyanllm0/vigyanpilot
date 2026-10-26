# GSC Submission Workflow — Week-3 Batch (8 comparison pages + 1 blog post)

**STATUS: ✅ SUBMITTED 2026-10-26 — all 9 successfully. Week 3 closed.**

- 8 comparison pages live since 2026-10-26 (surgical S3 upload + invalidation `IABG40HEBX5D2VPHO3X2XX00RY`)
- Blog post `/blog/vigyanllm-explained` live since 2026-10-25 (deploy `ICRQP3DLF1U03VY2OHT5JIW04I`, commit `504ba4f9`)
- All 9 verified 200 / 0 hops / canonical exact on day 0 (`scripts/pre_gsc_check.sh` 9/9 PASS)
- Sitemap resubmitted 2026-10-26: **Success, 419 URLs discovered**
- Request Indexing batch 2026-10-26: **9/9 submitted successfully, 0 errors** (owner-side, in GSC priority order)
- IndexNow ping for the blog post: HTTP 200 (Bing/Yandex; Google hint only)

## URLs (9)

```
https://www.vigyanllm.in/blog/vigyanllm-explained
https://www.vigyanllm.in/free-primer-design-tool
https://www.vigyanllm.in/free-molecular-docking
https://www.vigyanllm.in/primer-design-software-comparison
https://www.vigyanllm.in/msa-tools-comparison
https://www.vigyanllm.in/free-blast-alternative
https://www.vigyanllm.in/free-msa-software
https://www.vigyanllm.in/blast-vs-bowtie2
https://www.vigyanllm.in/autodock-vs-vina
```

## Day 1 — 2026-10-26 ✅ DONE

- [x] GSC → Sitemaps → resubmit `https://www.vigyanllm.in/sitemap.xml` → **Success, 419 URLs**
- [x] GSC → URL Inspection → **Request Indexing ×9** → 9/9 successful, 0 errors (10/day quota respected, no 10th URL)
- [x] Day-0 baseline captured: `docs/seo-week3/baselines/` (commit `4457f38a`)

## Day 7 — first indexation check — due 2026-11-02

- [ ] URL Inspection on all 9 → status should read **"URL is on Google"**
- [ ] Any still "Discovered – currently not indexed"? Note in KPI sheet; not a defect at day 7

## Day 14 — first ranking check — due 2026-11-09

- [ ] GSC → Performance → filter → "Pages" → enter `/autodock-vs-vina` etc.
- [ ] Record position + impressions per page in `docs/seo-week3/kpi-template.csv`
- [ ] Target: ≥7/9 indexed, 10–50 impressions each

## Day 30 — first report — due 2026-11-25

- [ ] Export 28-day Performance (Page + Query) → fill KPI sheet → trigger action items
- [ ] Compare vs verified baseline (`docs/seo-week3/baselines/README.md`):
      clicks 1,262 → 1,500–1,900 · impr 137K → 165–205K · CTR ≥1.0% · critical issues <100

## Verification script (local, any time)

```bash
bash scripts/verify_week3_postpush.sh          # 8 pages + sitemap + robots (66 checks)
bash scripts/verify_week3_postpush.sh --full   # + sweep all sitemap URLs for non-200
```

Last run 2026-10-26: 66/66 PASS, exit 0.
