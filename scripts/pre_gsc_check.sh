#!/usr/bin/env bash
# Pre-GSC submission check — verify every URL is live/canonical BEFORE
# Request Indexing in Search Console (submitting a 404/redirect burns
# the ~10 URL/day GSC quota).
#
# Usage:
#   bash scripts/pre_gsc_check.sh                 # default: current batch
#   BASE=https://staging.example bash scripts/pre_gsc_check.sh
#   URLS="a b c" bash scripts/pre_gsc_check.sh    # space-separated slugs
#
# Darwin-safe: no `grep -P` (BSD grep lacks PCRE), no read-only var names
# (zsh reserves `status`). Verified on macOS + bash 3.2.
set -u

BASE="${BASE:-https://www.vigyanllm.in}"
SLUGS=${URLS:-}
if [ -z "$SLUGS" ]; then
  SLUGS="autodock-vs-vina
blast-vs-bowtie2
free-blast-alternative
free-molecular-docking
free-msa-software
free-primer-design-tool
msa-tools-comparison
primer-design-software-comparison
blog/vigyanllm-explained"
fi

FAIL=0
COUNT=0
for slug in $SLUGS; do
  COUNT=$((COUNT + 1))
  url="$BASE/$slug"
  code=$(curl -o /dev/null -s -w "%{http_code}" --max-time 25 "$url")
  hops=$(curl -o /dev/null -s -w "%{num_redirects}" -L --max-time 25 "$url")
  canonical=$(curl -sL --max-time 25 "$url" \
    | grep -o 'rel="canonical" href="[^"]*"' | head -1 \
    | sed 's/.*href="//;s/"$//')

  if [ "$code" = "200" ] && [ "$hops" = "0" ] && [ "$canonical" = "$url" ]; then
    echo "  OK   $slug -> 200, 0 hops, canonical exact"
  else
    echo "  FAIL $slug -> status=$code hops=$hops canonical=$canonical"
    FAIL=1
  fi
done

echo ""
if [ "$FAIL" -eq 0 ]; then
  echo "ALL $COUNT URLS READY — open GSC and submit"
  echo "Sitemap URL to submit: $BASE/sitemap.xml"
else
  echo "FIX FAILURES BEFORE SUBMITTING TO GSC (each bad URL burns quota)"
  exit 1
fi
