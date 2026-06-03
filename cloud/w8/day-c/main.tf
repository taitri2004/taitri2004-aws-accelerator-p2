# main.tf — W8-D3 (T4) root module
# Mục tiêu: DRY — viết module 1 lần, GỌI NHIỀU LẦN với input khác nhau.
# Tạo 2 bucket (data + logs) từ cùng 1 module secure-bucket.

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

  # ──────────────────────────────────────────────────────────────
  # REMOTE STATE: mặc định để local cho lab. Khi muốn thử remote
  # state (Module 04), xem file backend.tf.example và bỏ comment.
  # ──────────────────────────────────────────────────────────────
}

provider "aws" {
  region = var.region
  default_tags {
    tags = {
      project    = "aws-accelerator-p2"
      week       = "w8"
      day        = "day-c"
      managed_by = "terraform"
    }
  }
}

resource "random_id" "suffix" {
  byte_length = 4
}

# Gọi module lần 1 — bucket chứa data
module "data_bucket" {
  source            = "./modules/secure-bucket"
  bucket_name       = "w8d3-data-${random_id.suffix.hex}"
  enable_versioning = true
  tags              = { role = "data" }
}

# Gọi module lần 2 — bucket chứa logs (cùng module, input khác)
module "logs_bucket" {
  source            = "./modules/secure-bucket"
  bucket_name       = "w8d3-logs-${random_id.suffix.hex}"
  enable_versioning = false
  tags              = { role = "logs" }
}
