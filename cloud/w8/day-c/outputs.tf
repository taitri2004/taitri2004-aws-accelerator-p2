# outputs.tf — root module: dùng output của các module con
# Cú pháp tham chiếu: module.<tên>.<output>

output "data_bucket_id" {
  value = module.data_bucket.bucket_id
}

output "data_bucket_arn" {
  value = module.data_bucket.bucket_arn
}

output "logs_bucket_id" {
  value = module.logs_bucket.bucket_id
}

output "logs_bucket_arn" {
  value = module.logs_bucket.bucket_arn
}
