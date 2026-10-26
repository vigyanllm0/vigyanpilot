#!/usr/bin/env bash
# 72-hour post-deploy verifier — 8 Week-3 comparison pages.
#
# Usage:
#   bash scripts/verify_week3_postpush.sh          # 8 pages + sitemap + robots
#   bash scripts/verify_week3_postpush.sh --full   # + HTTP sweep of every sitemap URL
#   BASE=https://staging.example bash scripts/verify_week3_postpush.sh
#
# Exit 0 = all checks pass. Exit 1 = at least one FAIL.
set -u

BASE="${BASE:-https://www.vigyanllm.in}"
EXPECT_SITEMAP="${EXPECT_SITEMAP:-418}"
SLUGS=(
  autodock-vs-vina
  blast-vs-bowtie2
  free-blast-alternative
  free-molecular-docking
  free-msa-software
  free-primer-design-tool
  msa-tools-comparison
  primer-design-software-comparison
)

pass=0 fail=0
chk() { # chk <PASS|FAIL> <message>
  printf '  %-4s  %s\n' "$1" "$2"
  if [ "$1" = PASS ]; then pass=$((pass + 1)); else fail=$((fail + 1)); fi
}

TMP=$(mktemp -d)
trap 'rm -rf "$TMP"' EXIT

echo "=== 8 comparison pages — $BASE ==="
for s in "${SLUGS[@]}"; do
  url="$BASE/$s"
  echo "-- $url"
  code=$(curl -s -o /dev/null -w '%{http_code}' --max-time 30 "$url")
  hops=$(curl -s -o /dev/null -w '%{num_redirects}' -L --max-time 30 "$url")
  curl -sL --max-time 30 "$url" -o "$TMP/$s.html"

  if [ "$code" = 200 ]; then chk PASS "HTTP 200"; else chk FAIL "HTTP $code"; fi
  if [ "${hops:-99}" -le 1 ]; then chk PASS "redirect hops=$hops (max 1)"; else chk FAIL "redirect chain hops=$hops"; fi

  # Structural checks (title/meta/canonical/JSON-LD/FAQ mirror/internal links)
  out=$(python3 - "$TMP/$s.html" "$url" <<'PY'
import html as H, json, re, sys

path, url = sys.argv[1], sys.argv[2]
src = open(path, encoding="utf-8").read()
res = []


def add(ok, msg):
    res.append(("PASS" if ok else "FAIL", msg))


m = re.search(r'<link rel="canonical" href="([^"]+)"', src)
got = m.group(1) if m else "MISSING"
add(got == url, f"canonical == {url}" + ("" if got == url else f" (got {got})"))

t = re.search(r"<title>(.*?)</title>", src, re.S)
title = H.unescape(t.group(1).strip()) if t else ""
add(40 <= len(title) <= 60, f"title {len(title)}ch (target 40-60)")

d = re.search(r'name="description" content="([^"]*)"', src)
desc = H.unescape(d.group(1)) if d else ""
add(140 <= len(desc) <= 165, f"meta description {len(desc)}ch (target 140-165)")

blocks = re.findall(r'<script type="application/ld\+json">(.*?)</script>', src, re.S)
parsed, errs = [], []
for b in blocks:
    try:
        parsed.append(json.loads(b))
    except Exception as e:
        errs.append(str(e))
add(bool(blocks) and not errs and len(parsed) == len(blocks),
    f"JSON-LD {len(parsed)}/{len(blocks)} parse" + (f" err={errs[0]}" if errs else ""))

schema_faq = sum(len(blk.get("mainEntity", [])) for blk in parsed
                 if "FAQPage" in str(blk.get("@type", "")))
visible_faq = len(re.findall(r'class="faq-item"', src))
add(visible_faq > 0 and visible_faq == schema_faq,
    f"FAQ mirror visible={visible_faq} schema={schema_faq}")

body = re.sub(r"<head.*?</head>", "", src, flags=re.S)
inlinks = len(set(re.findall(r'href="(/(?![/ ])[^"]*)"', body)))
add(inlinks >= 50, f"unique internal links {inlinks} (floor 50)")

print("\n".join(f"{st}\t{msg}" for st, msg in res))
PY
)
  while IFS=$'\t' read -r st msg; do chk "$st" "$msg"; done <<< "$out"
done

echo "=== sitemap / robots ==="
n=$(curl -s --max-time 30 "$BASE/sitemap.xml" | grep -c "<loc>")
if [ "$n" -eq "$EXPECT_SITEMAP" ]; then chk PASS "sitemap $n URLs (expect $EXPECT_SITEMAP)"
else chk FAIL "sitemap $n URLs (expect $EXPECT_SITEMAP)"; fi
rc=$(curl -s -o /dev/null -w '%{http_code}' --max-time 30 "$BASE/robots.txt")
if [ "$rc" = 200 ]; then chk PASS "robots.txt 200"; else chk FAIL "robots.txt $rc"; fi

if [ "${1:-}" = "--full" ]; then
  echo "=== full sitemap sweep (every URL must be 200 after redirects) ==="
  curl -s --max-time 30 "$BASE/sitemap.xml" | grep -o '<loc>[^<]*' | sed 's/<loc>//' > "$TMP/urls"
  total=$(wc -l < "$TMP/urls" | tr -d ' ')
  xargs -a "$TMP/urls" -P 8 -I{} sh -c \
    'c=$(curl -s -o /dev/null -w "%{http_code}" -L --max-time 20 "{}"); [ "$c" = 200 ] || echo "$c {}"' \
    > "$TMP/bad" 2>/dev/null
  bad=$(wc -l < "$TMP/bad" | tr -d ' ')
  if [ "$bad" -eq 0 ]; then chk PASS "sitemap sweep $total/$total -> 200"
  else chk FAIL "sitemap sweep $bad non-200 of $total"; sed 's/^/         /' "$TMP/bad"; fi
fi

echo
echo "RESULT: $pass passed, $fail failed"
[ "$fail" -eq 0 ] || exit 1
