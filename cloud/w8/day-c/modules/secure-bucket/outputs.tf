# modules/secure-bucket/outputs.tf — giá trị module trả ra cho caller

output "bucket_id" {
  description = "ID (tên) của bucket"
  value       = aws_s3_bucket.this.id
}

output "bucket_arn" {
  description = "ARN của bucket"
  value       = aws_s3_bucket.this.arn
}
