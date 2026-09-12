#!/bin/bash
# Setup S3 bucket for VigyanLLM frontend
set -euo pipefail

BUCKET="vigyanllm-frontend"
REGION="ap-south-1"

# 1. Create bucket
aws s3 mb s3://$BUCKET --region $REGION

# 2. Enable versioning
aws s3api put-bucket-versioning --bucket $BUCKET --versioning-configuration Status=Enabled

# 3. Block all public access (CloudFront uses OAI)
aws s3api put-public-access-block --bucket $BUCKET \
  --public-access-block-configuration \
  BlockPublicAcls=true,IgnorePublicAcls=true,BlockPublicPolicy=true,RestrictPublicBuckets=true

# 4. Enable CORS for development
aws s3api put-bucket-cors --bucket $BUCKET --cors-configuration '{
  "CORSRules": [{
    "AllowedOrigins": ["https://www.vigyanllm.in", "https://vigyanllm.in"],
    "AllowedMethods": ["GET", "HEAD"],
    "AllowedHeaders": ["*"],
    "MaxAgeSeconds": 3600
  }]
}'

# 5. Set lifecycle rule for old versions
aws s3api put-bucket-lifecycle-configuration --bucket $BUCKET --lifecycle-configuration '{
  "Rules": [{
    "ID": "CleanupOldVersions",
    "Status": "Enabled",
    "NoncurrentVersionExpiration": {"NoncurrentDays": 30}
  }]
}'

echo "S3 bucket ready: s3://$BUCKET"
