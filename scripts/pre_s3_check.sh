#!/usr/bin/env bash
# Pre-S3 deploy identity gate — run BEFORE any `aws s3` / `aws cloudfront` op.
#
# Why: on 2026-11-02 ~/.aws/credentials and the shell env were overwritten
# with an `amazon-bedrock_deploy-1` key (same account, DIFFERENT IAM user).
# Every `aws s3` call then 403'd on the vigyanllm-frontend bucket — and env
# credentials silently SHADOW all profiles, so a restored profile alone is
# not enough. See docs/seo-week3/ticket-aws-credential-conflict.md.
#
# Usage:  bash scripts/pre_s3_check.sh
# Exit 0 = the identity that will actually be used is user/vigyanllm-deploy.
# Exit 1 = wrong/unknown identity — do NOT run S3 operations.
#
# Darwin-safe: no `grep -P`, bash 3.2 compatible.

set -u

EXPECTED="arn:aws:iam::497862079867:user/vigyanllm-deploy"
PROFILE="${AWS_S3_PROFILE:-vigyanllm-deploy}"

if [ -n "${AWS_ACCESS_KEY_ID:-}" ]; then
  # Env credentials take precedence over EVERY profile — check them directly.
  ACTUAL=$(aws sts get-caller-identity --query Arn --output text 2>/dev/null || echo "ERROR: sts failed")
  SRC="env AWS_ACCESS_KEY_ID (shadows all profiles)"
else
  ACTUAL=$(AWS_PROFILE="$PROFILE" aws sts get-caller-identity --query Arn --output text 2>/dev/null || echo "ERROR: sts failed")
  SRC="profile $PROFILE"
fi

echo "deploy identity ($SRC): $ACTUAL"

if [ "$ACTUAL" = "$EXPECTED" ]; then
  echo "OK — identity verified, safe to run S3 operations."
  exit 0
fi

echo "REFUSED — expected: $EXPECTED"
echo
echo "Likely causes / fixes:"
if [ -n "${AWS_ACCESS_KEY_ID:-}" ]; then
  echo "  * Shell env is carrying foreign credentials (they shadow profiles)."
  echo "    For this deploy run:"
  echo "      env -u AWS_ACCESS_KEY_ID -u AWS_SECRET_ACCESS_KEY AWS_PROFILE=$PROFILE aws <subcommand>"
  echo "    or export the correct key instead."
fi
echo "  * Check ~/.aws/credentials has a [${PROFILE}] section (restored 2026-11-05)."
echo "  * Do NOT proceed with S3/CloudFront operations on this identity."
exit 1
