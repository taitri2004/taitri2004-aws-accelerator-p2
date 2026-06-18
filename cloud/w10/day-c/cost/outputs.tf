# outputs.tf
output "anomaly_monitor_arn" {
  description = "ARN cua Cost Anomaly Monitor"
  value       = aws_ce_anomaly_monitor.this.arn
}

output "anomaly_subscription_arn" {
  description = "ARN cua Cost Anomaly Subscription"
  value       = aws_ce_anomaly_subscription.this.arn
}
