#!/usr/bin/env bash
# Package Lambda@Edge function for deployment
# Run from this directory: cd deploy/aws/lambda-edge && bash package.sh

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
OUT="$SCRIPT_DIR/csp-headers.zip"

rm -f "$OUT"
cd "$SCRIPT_DIR"
zip -j "$OUT" csp-headers.py

echo "Packaged: $OUT ($(du -h "$OUT" | cut -f1))"
