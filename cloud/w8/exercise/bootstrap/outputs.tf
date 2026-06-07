output "state_bucket" {
  description = "S3 bucket used by the environments/dev backend"
  value       = aws_s3_bucket.state.id
}
