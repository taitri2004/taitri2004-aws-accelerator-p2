# outputs.tf — giá trị xuất ra sau apply

output "bucket_name" {
  description = "Tên bucket đã tạo"
  value       = aws_s3_bucket.this.id
}

output "bucket_arn" {
  description = "ARN của bucket"
  value       = aws_s3_bucket.this.arn
}

output "account_id" {
  description = "AWS account đang dùng (đọc từ data source)"
  value       = data.aws_caller_identity.current.account_id
}

output "region" {
  description = "Region đang deploy"
  value       = data.aws_region.current.region
}
