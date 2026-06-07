output "web_url" {
  description = "Web URL after apply"
  value       = "http://${module.ec2.public_ip}"
}

output "web_public_ip" {
  value = module.ec2.public_ip
}

output "rds_endpoint" {
  description = "Private MySQL endpoint"
  value       = module.rds.endpoint
}

output "assets_bucket" {
  value = module.s3.bucket_id
}

output "vpc_id" {
  value = module.vpc.vpc_id
}
