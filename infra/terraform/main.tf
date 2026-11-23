terraform {
  required_version = ">= 1.5.0"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}

provider "aws" {
  region = var.aws_region
}

variable "aws_region" {
  default = "ap-southeast-2" # Sydney region
}

variable "project_prefix" {
  default = "msme-cashflow-underwriting"
}

resource "random_id" "bucket_suffix" {
  byte_length = 4
}

locals {
  medallion_layers = ["bronze", "silver", "gold", "ml-registry"]
}

resource "aws_s3_bucket" "medallion" {
  for_each = toset(local.medallion_layers)
  bucket   = "${var.project_prefix}-${each.key}-${random_id.bucket_suffix.hex}"
}

resource "aws_s3_bucket_public_access_block" "medallion_block" {
  for_each                = aws_s3_bucket.medallion
  bucket                  = each.value.id
  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

output "bucket_names" {
  value = { for k, b in aws_s3_bucket.medallion : k => b.bucket }
}
