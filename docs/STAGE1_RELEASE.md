# Stage 1 Pharma Release — One-Command Procedure

**Status:** HELD (founder sign-off required)
**Trigger:** Founder says "go" after reviewing PHARMA_DATASET.md

## Release Command (10 minutes)

```bash
# 1. Flip the release switch
sed -i 's/^HELD_FOR_SIGNOFF = \[/HELD_FOR_SIGNOFF = [/' generate_sitemap.py
# Edit generate_sitemap.py: change HELD_FOR_SIGNOFF list to empty []
# Or: python3 -c "import re; f=open('generate_sitemap.py').read(); f=f.replace('HELD_FOR_SIGNOFF = [','HELD_FOR_SIGNOFF = [  # RELEASED'); open('generate_sitemap.py','w').write(f)"

# 2. Regenerate sitemap (pharma URLs now included)
python3 generate_sitemap.py

# 3. Sync frontend (pharma pages now public)
bash deploy/aws/sync-frontend.sh

# 4. Invalidate CloudFront
aws cloudfront create-invalidation --distribution-id E394TCXPIP8P6R --paths "/pharma-calculators" "/antibiotic-stock-calculator" "/pk-pd-calculator" "/osmolarity-calculator" "/dose-response-calculator" "/antibiotic-synergy-calculator" "/time-kill-calculator" "/mpc-calculator" "/arrhenius-calculator" "/protein-binding-calculator" "/cloning-simulator" "/sitemap.xml"

# 5. IndexNow flagship
curl -X POST https://api.indexnow.org/indexnow -H "Content-Type: application/json" -d '{"host":"www.vigyanllm.in","key":"<INDEXNOW_KEY>","urlList":["https://www.vigyanllm.in/pharma-calculators",...]}'
```

## Nav Partial (prepared, not deployed)

The "Pharma & Lab" nav category is prepared in a staged state.
To activate: apply the nav partial edits from the prepared branch, bake, sync, invalidate.

## Rollback

```bash
git revert <release-commit>
python3 generate_sitemap.py  # re-holds pharma URLs
bash deploy/aws/sync-frontend.sh
# invalidate same paths
```