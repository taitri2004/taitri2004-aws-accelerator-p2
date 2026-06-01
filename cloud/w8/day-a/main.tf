# main.tf — W8-D1 Terraform practice

# 1) terraform block: pin version Terraform + providers
terraform {
  required_version = ">= 1.10"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 6.0"
    }
    random = {
      source  = "hashicorp/random"
      version = "~> 3.6"
    }
  }
}

# 2) provider: đọc credentials từ AWS CLI bạn đã `aws configure`
#    default_tags: tự gắn tag cho MỌI resource (best practice)
provider "aws" {
  region = var.region

  default_tags {
    tags = {
      project    = "aws-accelerator-p2"
      week       = "w8"
      day        = "day-a"
      managed_by = "terraform"
    }
  }
}

# 3) data sources: đọc thông tin có sẵn, không tạo resource mới
data "aws_caller_identity" "current" {}
data "aws_region" "current" {}

# 4) random suffix: tên bucket S3 phải DUY NHẤT toàn cầu
resource "random_id" "suffix" {
  byte_length = 4
}

# 5) S3 bucket
resource "aws_s3_bucket" "this" {
  bucket = "${var.bucket_base_name}-${random_id.suffix.hex}"
}

# 6) Bật versioning (giữ lịch sử object)
resource "aws_s3_bucket_versioning" "this" {
  bucket = aws_s3_bucket.this.id
  versioning_configuration {
    status = "Enabled"
  }
}

# 7) Mã hoá server-side mặc định (AES256)
resource "aws_s3_bucket_server_side_encryption_configuration" "this" {
  bucket = aws_s3_bucket.this.id
  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}

# 8) Chặn mọi truy cập public
resource "aws_s3_bucket_public_access_block" "this" {
  bucket = aws_s3_bucket.this.id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}
