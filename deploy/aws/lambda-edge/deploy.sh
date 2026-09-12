#!/usr/bin/env bash
# Deploy CSP Lambda@Edge function to AWS
#
# Prerequisites:
#   1. AWS CLI configured (aws configure) with credentials that can:
#      - Create/update Lambda functions in us-east-1
#      - Attach IAM policies (Lambda execution role)
#   2. A Lambda execution role ARN with basic Lambda execution permissions
#      (CloudWatch Logs). Create one if needed:
#        aws iam create-role \
#          --role-name lambda-edge-csp-role \
#          --assume-role-policy-document '{"Version":"2012-10-17","Statement":[{"Effect":"Allow","Principal":{"Service":"lambda.amazonaws.com"},"Action":"sts:AssumeRole"}]}' \
#          --query 'Role.Arn' --output text
#        aws iam attach-role-policy \
#          --role-name lambda-edge-csp-role \
#          --policy-arn arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole
#
# Usage:
#   bash deploy.sh                          # create/update function only
#   bash deploy.sh --associate CF_DIST_ID   # also associate with CloudFront
#
# Lambda@Edge must be in us-east-1 regardless of where CloudFront is.

set -euo pipefail

REGION="us-east-1"
FUNCTION_NAME="vigyanllm-csp-headers"
RUNTIME="python3.9"
HANDLER="csp-headers.handler"
MEMORY=128
TIMEOUT=5
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
ZIP="$SCRIPT_DIR/csp-headers.zip"

# ---------------------------------------------------------------------------
# Preflight
# ---------------------------------------------------------------------------
if ! command -v aws &>/dev/null; then
  echo "ERROR: aws CLI not found. Install: https://aws.amazon.com/cli/"
  exit 1
fi

if [[ ! -f "$ZIP" ]]; then
  echo "ZIP not found — packaging first..."
  bash "$SCRIPT_DIR/package.sh"
fi

# Execution role
ROLE_ARN="${LAMBDA_EXEC_ROLE_ARN:-}"
if [[ -z "$ROLE_ARN" ]]; then
  echo ""
  echo "No LAMBDA_EXEC_ROLE_ARN set."
  echo "Create one with:"
  echo "  aws iam create-role --role-name lambda-edge-csp-role \\"
  echo "    --assume-role-policy-document '{\"Version\":\"2012-10-17\",\"Statement\":[{\"Effect\":\"Allow\",\"Principal\":{\"Service\":\"lambda.amazonaws.com\"},\"Action\":\"sts:AssumeRole\"}]}' \\"
  echo "    --query 'Role.Arn' --output text"
  echo ""
  echo "Then set: export LAMBDA_EXEC_ROLE_ARN=arn:aws:iam::ACCOUNT:role/lambda-edge-csp-role"
  exit 1
fi

# ---------------------------------------------------------------------------
# Create or update function
# ---------------------------------------------------------------------------
echo "Deploying $FUNCTION_NAME to $REGION..."

if aws lambda get-function \
    --function-name "$FUNCTION_NAME" \
    --region "$REGION" \
    --no-cli-pager &>/dev/null; then
  echo "Function exists — updating code..."
  aws lambda update-function-code \
    --function-name "$FUNCTION_NAME" \
    --region "$REGION" \
    --zip-file "fileb://$ZIP" \
    --no-cli-pager

  echo "Updating configuration..."
  aws lambda update-function-configuration \
    --function-name "$FUNCTION_NAME" \
    --region "$REGION" \
    --runtime "$RUNTIME" \
    --handler "$HANDLER" \
    --role "$ROLE_ARN" \
    --memory-size "$MEMORY" \
    --timeout "$TIMEOUT" \
    --no-cli-pager
else
  echo "Creating new function..."
  aws lambda create-function \
    --function-name "$FUNCTION_NAME" \
    --region "$REGION" \
    --runtime "$RUNTIME" \
    --handler "$HANDLER" \
    --role "$ROLE_ARN" \
    --memory-size "$MEMORY" \
    --timeout "$TIMEOUT" \
    --zip-file "fileb://$ZIP" \
    --no-cli-pager
fi

echo ""
echo "Function deployed: $FUNCTION_NAME"
echo "Region: $REGION"
echo "Runtime: $RUNTIME | Memory: ${MEMORY}MB | Timeout: ${TIMEOUT}s"

# ---------------------------------------------------------------------------
# CloudFront association (optional)
# ---------------------------------------------------------------------------
if [[ "${1:-}" == "--associate" ]]; then
  CF_DIST_ID="${2:-}"
  if [[ -z "$CF_DIST_ID" ]]; then
    echo "Usage: bash deploy.sh --associate <CLOUDFRONT_DISTRIBUTION_ID>"
    exit 1
  fi

  # Get function ARN (must be qualified with version for Lambda@Edge)
  echo ""
  echo "Publishing version..."
  VERSION=$(aws lambda publish-version \
    --function-name "$FUNCTION_NAME" \
    --region "$REGION" \
    --no-cli-pager \
    --query 'Version' --output text)
  echo "Published version: $VERSION"

  FUNCTION_ARN="arn:aws:lambda:${REGION}:$(aws sts get-caller-identity --query Account --output text):function:${FUNCTION_NAME}:${VERSION}"

  echo ""
  echo "Associating with CloudFront distribution: $CF_DIST_ID"
  echo "NOTE: Lambda@Edge must be associated via CloudFront API, not CLI directly."
  echo ""
  echo "Use the AWS Console or this CLI command:"
  echo ""
  echo "  aws cloudfront update-distribution \\"
  echo "    --id $CF_DIST_ID \\"
  echo "    --distribution-config file://<(aws cloudfront get-distribution-config --id $CF_DIST_ID --query 'DistributionConfig' --output json | \\"
  echo "      jq '.DefaultCacheBehavior.LambdaFunctionAssociations.Items += [{\"LambdaFunctionARN\":\"$FUNCTION_ARN\",\"EventType\":\"origin-response\",\"IncludeBody\":false}]')"
  echo ""
  echo "Or add via the CloudFront console: Behaviors → Default behavior → Lambda Function Associations → Add origin-response."
  echo "Lambda function ARN: $FUNCTION_ARN"
fi

echo ""
echo "Done."
