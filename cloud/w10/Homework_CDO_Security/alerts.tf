resource "aws_sns_topic" "alerts" {
  name = "${var.name}-macie-alerts"
}

resource "aws_sns_topic_subscription" "email" {
  topic_arn = aws_sns_topic.alerts.arn
  protocol  = "email"
  endpoint  = var.alert_email
}

resource "aws_sns_topic_policy" "allow_events" {
  arn = aws_sns_topic.alerts.arn
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Sid       = "AllowEventBridgePublish"
      Effect    = "Allow"
      Principal = { Service = "events.amazonaws.com" }
      Action    = "sns:Publish"
      Resource  = aws_sns_topic.alerts.arn
    }]
  })
}

resource "aws_cloudwatch_event_rule" "macie_finding" {
  name        = "${var.name}-macie-finding"
  description = "Bat Macie sensitive-data findings"
  event_pattern = jsonencode({
    source      = ["aws.macie"]
    detail-type = ["Macie Finding"]
  })
}

resource "aws_cloudwatch_event_target" "to_sns" {
  rule      = aws_cloudwatch_event_rule.macie_finding.name
  target_id = "sns"
  arn       = aws_sns_topic.alerts.arn

  input_transformer {
    input_paths = {
      severity = "$.detail.severity.description"
      type     = "$.detail.type"
      bucket   = "$.detail.resourcesAffected.s3Bucket.name"
    }
    input_template = "\"[Macie] phat hien du lieu nhay cam | Severity: <severity> | Type: <type> | Bucket: <bucket>\""
  }
}
