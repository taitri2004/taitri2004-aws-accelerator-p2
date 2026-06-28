terraform {
  required_version = ">= 1.5"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.40"
    }
    kubernetes = {
      source  = "hashicorp/kubernetes"
      version = "~> 2.27"
    }
  }

  # Remote state — mở sau khi bootstrap S3 bucket (xem README).
  # Dùng S3 native lockfile (Terraform >= 1.10) → không cần DynamoDB lock table.
  # backend "s3" {
  #   bucket       = "tf-3-cdo2-tfstate"
  #   key          = "sandbox/terraform.tfstate"
  #   region       = "us-east-1"
  #   use_lockfile = true
  #   encrypt      = true
  # }
}
