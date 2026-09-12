#!/bin/bash
# Sync frontend files to S3 with cache headers
set -euo pipefail

BUCKET="s3://vigyanllm-frontend"
FRONTEND="frontend"

echo "Syncing frontend to S3..."

# Upload fonts with 1-year immutable cache
aws s3 sync $FRONTEND/ $BUCKET/ \
  --exclude "*" \
  --include "*.woff" --include "*.woff2" --include "*.ttf" --include "*.otf" --include "*.eot" \
  --cache-control "public, max-age=31536000, immutable" \
  --delete

# Upload images with 1-day immutable cache
aws s3 sync $FRONTEND/ $BUCKET/ \
  --exclude "*" \
  --include "*.png" --include "*.jpg" --include "*.jpeg" --include "*.gif" --include "*.webp" --include "*.ico" --include "*.svg" \
  --cache-control "public, max-age=86400, immutable" \
  --delete

# Upload JS with stale-while-revalidate
aws s3 sync $FRONTEND/ $BUCKET/ \
  --exclude "*" --include "*.js" \
  --cache-control "public, max-age=86400, stale-while-revalidate=604800" \
  --delete

# Upload CSS with stale-while-revalidate
aws s3 sync $FRONTEND/ $BUCKET/ \
  --exclude "*" --include "*.css" \
  --cache-control "public, max-age=86400, stale-while-revalidate=604800" \
  --delete

# Upload HTML with short cache
aws s3 sync $FRONTEND/ $BUCKET/ \
  --exclude "*" --include "*.html" \
  --cache-control "public, max-age=300, stale-while-revalidate=600" \
  --delete

# Upload JSON, XML with 1-hour cache
aws s3 sync $FRONTEND/ $BUCKET/ \
  --exclude "*" --include "*.json" --include "*.xml" \
  --cache-control "public, max-age=3600" \
  --delete

# Upload everything else with default cache
aws s3 sync $FRONTEND/ $BUCKET/ \
  --cache-control "public, max-age=86400" \
  --delete

echo "Sync complete. Verifying..."
aws s3 ls $BUCKET/ --recursive | wc -l
echo "files uploaded"
