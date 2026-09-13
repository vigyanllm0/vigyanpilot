#!/bin/bash
# Deploy CloudFront response headers policy
# Run: bash deploy/aws/deploy-headers-policy.sh

set -euo pipefail

POLICY_ID=$(aws cloudfront list-response-headers-policies --query "ResponseHeadersPolicyList.Items[?Name=='vigyanllm-security-headers'].Id" --output text 2>/dev/null || echo "")

if [ -z "$POLICY_ID" ]; then
  echo "Creating new response headers policy..."
  POLICY_ID=$(aws cloudfront create-response-headers-policies \
    --response-headers-policy-config file://deploy/aws/cloudfront-headers-policy.json \
    --query 'ResponseHeadersPolicy.Id' --output text)
  echo "Created policy: $POLICY_ID"
else
  echo "Updating existing policy: $POLICY_ID"
  aws cloudfront update-response-headers-policies \
    --id "$POLICY_ID" \
    --response-headers-policy-config file://deploy/aws/cloudfront-headers-policy.json
fi

# Update CloudFront distribution to use this policy
DIST_ID="E394TCXPIP8P6R"
ETAG=$(aws cloudfront get-distribution-config --id "$DIST_ID" --query 'ETag' --output text)

# Get current config, add response headers policy, update
aws cloudfront get-distribution-config --id "$DIST_ID" --query 'DistributionConfig' --output json > /tmp/distribution-config.json

# Add DefaultCacheBehavior.ResponseHeadersPolicyId
python3 -c "
import json
with open('/tmp/distribution-config.json') as f:
    config = json.load(f)
config['DefaultCacheBehavior']['ResponseHeadersPolicyId'] = '$POLICY_ID'
with open('/tmp/distribution-config-new.json', 'w') as f:
    json.dump(config, f)
"

aws cloudfront update-distribution \
  --id "$DIST_ID" \
  --if-match "$ETAG" \
  --distribution-config file:///tmp/distribution-config-new.json

echo "Distribution updated. Changes deploy in 5-15 minutes."
