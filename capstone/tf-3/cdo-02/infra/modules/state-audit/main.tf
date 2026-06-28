data "aws_caller_identity" "current" {}

# ---- KMS CMK cho audit (03_security_design §4) ----
resource "aws_kms_key" "audit" {
  description             = "${var.name} audit trail CMK"
  enable_key_rotation     = true
  deletion_window_in_days = 7
  tags                    = var.tags
}

resource "aws_kms_alias" "audit" {
  name          = "alias/${var.name}-audit"
  target_key_id = aws_kms_key.audit.key_id
}

# ---- S3 audit bucket, Object Lock Compliance (ADR-004) ----
resource "aws_s3_bucket" "audit" {
  bucket              = "${var.name}-audit-${data.aws_caller_identity.current.account_id}"
  object_lock_enabled = true # phải bật lúc tạo bucket
  tags                = var.tags
}

resource "aws_s3_bucket_versioning" "audit" {
  bucket = aws_s3_bucket.audit.id
  versioning_configuration {
    status = "Enabled" # Object Lock yêu cầu versioning
  }
}

resource "aws_s3_bucket_object_lock_configuration" "audit" {
  bucket = aws_s3_bucket.audit.id
  rule {
    default_retention {
      mode = "COMPLIANCE" # không ai (kể cả root) xóa/sửa trong retention
      days = var.audit_retention_days
    }
  }
}

resource "aws_s3_bucket_server_side_encryption_configuration" "audit" {
  bucket = aws_s3_bucket.audit.id
  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm     = "aws:kms"
      kms_master_key_id = aws_kms_key.audit.arn
    }
  }
}

resource "aws_s3_bucket_public_access_block" "audit" {
  bucket                  = aws_s3_bucket.audit.id
  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

resource "aws_s3_bucket_lifecycle_configuration" "audit" {
  bucket = aws_s3_bucket.audit.id
  rule {
    id     = "tier-after-hot"
    status = "Enabled"
    filter {}
    transition {
      days          = var.audit_retention_days
      storage_class = "GLACIER"
    }
  }
}

# ---- DynamoDB idempotency lock (deployment contract §5.A) ----
resource "aws_dynamodb_table" "idempotency" {
  name         = "${var.name}-idempotency-lock"
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "idempotency_key"

  attribute {
    name = "idempotency_key"
    type = "S"
  }

  ttl {
    attribute_name = "expires_at"
    enabled        = true
  }

  tags = var.tags
}
