terraform {
  required_version = ">= 1.7"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }

  backend "s3" {
    bucket         = "earthandyou-terraform-state"
    key            = "staging/terraform.tfstate"
    region         = "ap-southeast-1"
    dynamodb_table = "earthandyou-terraform-locks"
    encrypt        = true
  }
}

provider "aws" {
  region = var.aws_region
}
