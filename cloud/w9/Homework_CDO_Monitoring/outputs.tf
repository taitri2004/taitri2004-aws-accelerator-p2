output "instance_id" {
  description = "EC2 instance id"
  value       = aws_instance.this.id
}

output "ssm_start_session" {
  description = "Vao instance bang SSM de chay stress test"
  value       = "aws ssm start-session --target ${aws_instance.this.id} --region ${var.region}"
}

output "alarm_name" {
  description = "Ten CloudWatch alarm"
  value       = aws_cloudwatch_metric_alarm.cpu_high.alarm_name
}
