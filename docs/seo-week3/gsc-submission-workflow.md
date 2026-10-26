# GSC Submission Workflow — 8 Week-3 Comparison Pages

Live since 2026-10-26 (deploy: surgical S3 upload + invalidation `IABG40HEBX5D2VPHO3X2XX00RY`).
All 8 verified 200 / canonical / valid FAQ schema on day 0.

## URLs (8)

```
https://www.vigyanllm.in/autodock-vs-vina
https://www.vigyanllm.in/blast-vs-bowtie2
https://www.vigyanllm.in/free-blast-alternative
https://www.vigyanllm.in/free-molecular-docking
https://www.vigyanllm.in/free-msa-software
https://www.vigyanllm.in/free-primer-design-tool
https://www.vigyanllm.in/msa-tools-comparison
https://www.vigyanllm.in/primer-design-software-comparison
```

## Day 1 (today)

- [ ] GSC → Sitemaps → resubmit `https://www.vigyanllm.in/sitemap.xml` → expect **Success**, 418 URLs read
      (it was already submitted; resubmit forces a fresh read of the 8 new entries)

## Day 2–3 (one batch — 10/day limit, 8 fits in a day)

- [ ] GSC → URL Inspection → paste URL → **Request Indexing** for each of the 8 (top to bottom)

## Day 7 — first indexation check

- [ ] URL Inspection on all 8 → status should read **"URL is on Google"**
- [ ] Any still "Discovery – currently not indexed"? Note in KPI sheet; not a defect at day 7

## Day 14 — first ranking check

- [ ] GSC → Performance → filter → "Pages" → enter `/autodock-vs-vina` etc.
- [ ] Record position + impressions per page in `docs/seo-week3/kpi-template.csv`

## Day 30 — first report

- [ ] Export 28-day Performance (Page + Query) → fill KPI sheet → trigger action items

## Verification script (local, any time)

```bash
bash scripts/verify_week3_postpush.sh          # 8 pages + sitemap + robots (66 checks)
bash scripts/verify_week3_postpush.sh --full   # + sweep all 418 sitemap URLs for non-200
```

Last run 2026-10-26: 66/66 PASS, exit 0.
