#!/bin/bash
set -euo pipefail

# -------------------------------------------------------
# Earth&You — Terraform Remote State Bootstrap
# Run this ONCE before any Terraform commands.
# Requires: AWS CLI configured with sufficient permissions.
# -------------------------------------------------------

AWS_REGION="ap-southeast-1"
STATE_BUCKET="earthandyou-terraform-state"
LOCK_TABLE="earthandyou-terraform-locks"
ENVIRONMENT="${1:-staging}"

echo "==> Bootstrapping Terraform remote state"
echo "    Region  : $AWS_REGION"
echo "    Bucket  : $STATE_BUCKET"
echo "    Table   : $LOCK_TABLE"
echo ""

# Create S3 bucket
if aws s3api head-bucket --bucket "$STATE_BUCKET" 2>/dev/null; then
  echo "==> S3 bucket already exists, skipping."
else
  echo "==> Creating S3 bucket..."
  aws s3api create-bucket \
    --bucket "$STATE_BUCKET" \
    --region "$AWS_REGION" \
    --create-bucket-configuration LocationConstraint="$AWS_REGION"

  aws s3api put-bucket-versioning \
    --bucket "$STATE_BUCKET" \
    --versioning-configuration Status=Enabled

  aws s3api put-bucket-encryption \
    --bucket "$STATE_BUCKET" \
    --server-side-encryption-configuration '{
      "Rules": [{
        "ApplyServerSideEncryptionByDefault": {
          "SSEAlgorithm": "AES256"
        }
      }]
    }'

  aws s3api put-public-access-block \
    --bucket "$STATE_BUCKET" \
    --public-access-block-configuration \
      "BlockPublicAcls=true,IgnorePublicAcls=true,BlockPublicPolicy=true,RestrictPublicBuckets=true"

  echo "==> S3 bucket created and secured."
fi

# Create DynamoDB table for state locking
if aws dynamodb describe-table --table-name "$LOCK_TABLE" --region "$AWS_REGION" 2>/dev/null; then
  echo "==> DynamoDB table already exists, skipping."
else
  echo "==> Creating DynamoDB lock table..."
  aws dynamodb create-table \
    --table-name "$LOCK_TABLE" \
    --attribute-definitions AttributeName=LockID,AttributeType=S \
    --key-schema AttributeName=LockID,KeyType=HASH \
    --billing-mode PAY_PER_REQUEST \
    --region "$AWS_REGION"

  echo "==> DynamoDB table created."
fi

echo ""
echo "==> Bootstrap complete."
echo "    You can now run Terraform in infrastructure/environments/$ENVIRONMENT"
