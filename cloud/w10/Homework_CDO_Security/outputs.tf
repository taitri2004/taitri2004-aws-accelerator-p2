output "bucket_name" {
  description = "Bucket chua sample files"
  value       = aws_s3_bucket.data.id
}

output "macie_job_id" {
  description = "Macie classification job id"
  value       = aws_macie2_classification_job.scan.job_id
}

output "sns_topic_arn" {
  description = "SNS topic gui canh bao"
  value       = aws_sns_topic.alerts.arn
}

output "macie_console" {
  description = "Mo Macie console xem findings"
  value       = "https://${var.region}.console.aws.amazon.com/macie/home?region=${var.region}#findings"
}

output "check_findings_cli" {
  description = "Liet ke finding qua CLI sau khi job chay xong"
  value       = "aws macie2 list-findings --region ${var.region}"
}
