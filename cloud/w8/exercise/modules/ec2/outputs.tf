output "public_ip" {
  value = aws_instance.web.public_ip
}

output "security_group_id" {
  description = "Web security group ID used by the RDS ingress rule"
  value       = aws_security_group.web.id
}
