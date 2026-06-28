output "audit_bucket" {
  value = aws_s3_bucket.audit.id
}

output "audit_kms_key_arn" {
  value = aws_kms_key.audit.arn
}

output "idempotency_table" {
  value = aws_dynamodb_table.idempotency.name
}
