# monitoring.tf - SNS topic + email subscription + CloudWatch CPU alarm
# Scenario: gui email khi EC2 CPU > 80% trong 5 phut lien tiep

# Slide buoc 1: SNS topic + email subscription (phai bam Confirm trong mail)
resource "aws_sns_topic" "alerts" {
  name = "${var.name}-alerts"
}

resource "aws_sns_topic_subscription" "email" {
  topic_arn = aws_sns_topic.alerts.arn
  protocol  = "email"
  endpoint  = var.alert_email
}

# Slide buoc 2-4: alarm CPUUtilization > 80%, period 5 phut, 1/1 datapoint
resource "aws_cloudwatch_metric_alarm" "cpu_high" {
  alarm_name          = "${var.name}-ec2-cpu-high"
  alarm_description   = "EC2 CPU > 80% trong 5 phut lien tiep"
  namespace           = "AWS/EC2"
  metric_name         = "CPUUtilization"
  statistic           = "Average"
  comparison_operator = "GreaterThanThreshold"
  threshold           = 80
  period              = 300
  evaluation_periods  = 1

  dimensions = {
    InstanceId = aws_instance.this.id
  }

  alarm_actions = [aws_sns_topic.alerts.arn]
  ok_actions    = [aws_sns_topic.alerts.arn] # recovery (slide: optional)
}
