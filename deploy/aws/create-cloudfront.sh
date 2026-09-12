#!/bin/bash
# Create CloudFront distribution for VigyanLLM frontend
set -euo pipefail

BUCKET="vigyanllm-frontend"
REGION="ap-south-1"
DOMAIN="vigyanllm.in"
WWW_DOMAIN="www.vigyanllm.in"

# --- PLACEHOLDER: Fill these in after creating resources ---
ALB_DNS="PLACEHOLDER_ALB_DNS"        # e.g. vigyanllm-alb-123456.ap-south-1.elb.amazonaws.com
ACM_CERT_ARN="PLACEHOLDER_ACM_ARN"   # e.g. arn:aws:acm:ap-south-1:123456789:certificate/abc-123
CF_FUNCTION_ARN="PLACEHOLDER_FUNCTION_ARN"  # Lambda@Edge or CloudFront Function ARN (optional)
# -------------------------------------------------------------

# 1. Create Origin Access Control
OAI_ID=$(aws cloudfront create-origin-access-control \
  --origin-access-control-config '{
    "Name": "vigyanllm-s3-oac",
    "SigningBehavior": "always",
    "SigningProtocol": "sigv4",
    "OriginAccessControlOriginType": "s3"
  }' \
  --query 'OriginAccessControl.Id' --output text)

echo "Created OAC: $OAI_ID"

# 2. Create CloudFront distribution
DIST_CONFIG=$(cat <<EOF
{
  "CallerReference": "vigyanllm-frontend-$(date +%s)",
  "Origins": {
    "Quantity": 2,
    "Items": [
      {
        "Id": "S3-${BUCKET}",
        "DomainName": "${BUCKET}.s3.${REGION}.amazonaws.com",
        "OriginAccessControlId": "${OAI_ID}",
        "S3OriginConfig": {
          "OriginAccessIdentity": ""
        }
      },
      {
        "Id": "ALB-API",
        "DomainName": "${ALB_DNS}",
        "CustomHeaders": {
          "Quantity": 0
        },
        "CustomOriginConfig": {
          "HTTPPort": 80,
          "HTTPSPort": 443,
          "OriginProtocolPolicy": "https-only",
          "OriginSslProtocols": {
            "Quantity": 1,
            "Items": ["TLSv1.2"]
          },
          "OriginReadTimeout": 60,
          "OriginKeepaliveTimeout": 5
        }
      }
    ]
  },
  "DefaultCacheBehavior": {
    "TargetOriginId": "S3-${BUCKET}",
    "ViewerProtocolPolicy": "redirect-to-https",
    "AllowedMethods": {
      "Quantity": 2,
      "Items": ["GET", "HEAD"]
    },
    "CachedMethods": {
      "Quantity": 2,
      "Items": ["GET", "HEAD"]
    },
    "ForwardedValues": {
      "QueryString": false,
      "Cookies": {"Forward": "none"},
      "Headers": {"Quantity": 0},
      "QueryStringCacheKeys": {"Quantity": 0}
    },
    "MinTTL": 0,
    "DefaultTTL": 86400,
    "MaxTTL": 31536000,
    "Compress": true,
    "FunctionAssociations": {
      "Quantity": 0
    },
    "ViewerRequestEventAssociation": {
      "FunctionARN": ""
    }
  },
  "CacheBehaviors": {
    "Quantity": 2,
    "Items": [
      {
        "PathPattern": "/api/*",
        "TargetOriginId": "ALB-API",
        "ViewerProtocolPolicy": "redirect-to-https",
        "AllowedMethods": {
          "Quantity": 7,
          "Items": ["GET", "HEAD", "OPTIONS", "PUT", "POST", "PATCH", "DELETE"]
        },
        "CachedMethods": {
          "Quantity": 2,
          "Items": ["GET", "HEAD"]
        },
        "ForwardedValues": {
          "QueryString": true,
          "Cookies": {"Forward": "all"},
          "Headers": {
            "Quantity": 5,
            "Items": [
              "Authorization",
              "Content-Type",
              "Origin",
              "Referer",
              "X-Forwarded-For"
            ]
          },
          "QueryStringCacheKeys": {"Quantity": 0}
        },
        "MinTTL": 0,
        "DefaultTTL": 0,
        "MaxTTL": 0,
        "Compress": false
      },
      {
        "PathPattern": "/health",
        "TargetOriginId": "ALB-API",
        "ViewerProtocolPolicy": "redirect-to-https",
        "AllowedMethods": {
          "Quantity": 2,
          "Items": ["GET", "HEAD"]
        },
        "CachedMethods": {
          "Quantity": 2,
          "Items": ["GET", "HEAD"]
        },
        "ForwardedValues": {
          "QueryString": false,
          "Cookies": {"Forward": "none"},
          "Headers": {"Quantity": 0},
          "QueryStringCacheKeys": {"Quantity": 0}
        },
        "MinTTL": 0,
        "DefaultTTL": 0,
        "MaxTTL": 0,
        "Compress": false
      }
    ]
  },
  "CustomErrorResponses": {
    "Quantity": 2,
    "Items": [
      {
        "ErrorCode": 404,
        "ResponsePagePath": "/404.html",
        "ResponseCode": "404",
        "ErrorCachingMinTTL": 300
      },
      {
        "ErrorCode": 403,
        "ResponsePagePath": "/404.html",
        "ResponseCode": "404",
        "ErrorCachingMinTTL": 300
      }
    ]
  },
  "Comment": "VigyanLLM frontend - ${DOMAIN}",
  "Enabled": true,
  "Aliases": {
    "Quantity": 2,
    "Items": ["${DOMAIN}", "${WWW_DOMAIN}"]
  },
  "ViewerCertificate": {
    "CloudFrontDefaultCertificate": false,
    "ACMCertificateArn": "${ACM_CERT_ARN}",
    "SSLSupportMethod": "sni-only",
    "MinimumProtocolVersion": "TLSv1.2_2021"
  },
  "PriceClass": "PriceClass_200",
  "Logging": {
    "Enabled": false
  }
}
EOF
)

RESULT=$(aws cloudfront create-distribution --distribution-config "$DIST_CONFIG")

DIST_ID=$(echo "$RESULT" | jq -r '.Distribution.Id')
DIST_DOMAIN=$(echo "$RESULT" | jq -r '.Distribution.DomainName')

echo ""
echo "=========================================="
echo "CloudFront distribution created"
echo "=========================================="
echo "Distribution ID: $DIST_ID"
echo "Domain name:     $DIST_DOMAIN"
echo ""
echo "Next steps:"
echo "  1. Update S3 bucket policy (run grant-s3-access.sh)"
echo "  2. Create ACM certificate for ${DOMAIN} + ${WWW_DOMAIN}"
echo "  3. Create DNS CNAME/A records pointing to ${DIST_DOMAIN}"
echo "  4. Update ALB_DNS in this script and re-run if needed"
echo "=========================================="
