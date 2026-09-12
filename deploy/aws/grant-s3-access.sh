#!/bin/bash
# Grant CloudFront OAC access to S3 bucket
set -euo pipefail

BUCKET="vigyanllm-frontend"
DIST_ID="PLACEHOLDER_DIST_ID"  # Fill in after create-cloudfront.sh

# Get the distribution's S3 origin domain
ORIGIN_DOMAIN=$(aws cloudfront get-distribution --id "$DIST_ID" \
  --query 'Distribution.DistributionConfig.Origins.Items[?Id==`S3-vigyanllm-frontend`].DomainName' \
  --output text)

# Extract the canonical user ID of the CloudFront service principal
# OAC uses the service principal, not a canonical user
cat <<POLICY | aws s3api put-bucket-policy --bucket "$BUCKET" --policy -
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "AllowCloudFrontServicePrincipal",
      "Effect": "Allow",
      "Principal": {
        "Service": "cloudfront.amazonaws.com"
      },
      "Action": "s3:GetObject",
      "Resource": "arn:aws:s3:::${BUCKET}/*",
      "Condition": {
        "StringEquals": {
          "AWS:SourceArn": "arn:aws:cloudfront::$(aws sts get-caller-identity --query Account --output text):distribution/${DIST_ID}"
        }
      }
    }
  ]
}
POLICY

echo "Bucket policy applied for CloudFront distribution: $DIST_ID"
