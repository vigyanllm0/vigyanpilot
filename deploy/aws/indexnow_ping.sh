#!/bin/bash
# IndexNow ping — run AFTER a frontend deploy (key file must be live first).
# Usage:
#   bash deploy/aws/indexnow_ping.sh                 # default: HQ-propagation pages + homepage
#   bash deploy/aws/indexnow_ping.sh <url> [<url>…]  # explicit URL list
# Key file: frontend/0ee8202c255a8c5a4098f5e60f9f831b.txt (served at site root).
# NOTE: deploy/aws/sync-frontend.sh is run-only and must NOT be edited — this is the companion ping step.
set -euo pipefail

KEY="0ee8202c255a8c5a4098f5e60f9f831b"
HOST="www.vigyanllm.in"

if [ "$#" -gt 0 ]; then
  URLS=("$@")
else
  URLS=(
    "https://www.vigyanllm.in"
    "https://www.vigyanllm.in/about"
    "https://www.vigyanllm.in/team"
    "https://www.vigyanllm.in/about/sovereign-ai"
    "https://www.vigyanllm.in/primer-design-india"
  )
fi

PAYLOAD=$(python3 - "$KEY" "$HOST" "${URLS[@]}" << 'EOF'
import json, sys
key, host, urls = sys.argv[1], sys.argv[2], sys.argv[3:]
print(json.dumps({"host": host, "key": key,
                  "keyLocation": f"https://{host}/{key}.txt",
                  "urlList": urls}))
EOF
)

echo "IndexNow ping -> ${#URLS[@]} URL(s)"
curl -sS -o /tmp/indexnow_resp.txt -w "HTTP %{http_code}\n" \
  -X POST "https://api.indexnow.org/indexnow" \
  -H "Content-Type: application/json; charset=utf-8" \
  --data "$PAYLOAD"
cat /tmp/indexnow_resp.txt; echo
echo "Done. (200 = received; 202 = received pending key validation; 4xx = fix key file.)"
