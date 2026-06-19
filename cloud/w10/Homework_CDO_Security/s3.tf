data "aws_caller_identity" "current" {}

resource "aws_s3_bucket" "data" {
  bucket        = "${var.name}-${data.aws_caller_identity.current.account_id}"
  force_destroy = true
}

resource "aws_s3_bucket_public_access_block" "data" {
  bucket                  = aws_s3_bucket.data.id
  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

resource "aws_s3_object" "samples" {
  for_each = fileset("${path.module}/sample-data", "*")
  bucket   = aws_s3_bucket.data.id
  key      = each.value
  source   = "${path.module}/sample-data/${each.value}"
  etag     = filemd5("${path.module}/sample-data/${each.value}")
}
