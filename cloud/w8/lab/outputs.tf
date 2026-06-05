output "alb_url" {
  description = "ALB URL for the web app"
  value       = "http://${aws_lb.this.dns_name}"
}

output "instance_id" {
  description = "EC2 instance id for SSM"
  value       = aws_instance.node.id
}

output "instance_public_ip" {
  description = "EC2 public IP"
  value       = aws_instance.node.public_ip
}

output "ssm_start_session" {
  description = "SSM Session Manager command"
  value       = "aws ssm start-session --target ${aws_instance.node.id} --region ${var.region}"
}
