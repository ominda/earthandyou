# Terraform Remote State Bootstrap

Run this **once** before any Terraform commands, from WSL2.

## Prerequisites

- AWS CLI configured (`aws configure`)
- IAM user/role with permissions to create S3 buckets and DynamoDB tables

## Run

```bash
cd scripts
chmod +x bootstrap_terraform_state.sh
./bootstrap_terraform_state.sh
```

## What it creates

| Resource | Name |
|----------|------|
| S3 bucket | `earthandyou-terraform-state` |
| S3 versioning | Enabled |
| S3 encryption | AES256 |
| S3 public access | Blocked |
| DynamoDB table | `earthandyou-terraform-locks` |

## After bootstrap

```bash
cd infrastructure/environments/staging
cp terraform.tfvars.example terraform.tfvars
terraform init
terraform plan
```
