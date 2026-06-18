# cost.tf - AWS Cost Anomaly Detection: monitor theo SERVICE + email canh bao
# Scenario: ML cua AWS hoc pattern chi tieu, gui email khi ton bat thuong
# (vd ai do bat cum GPU) vuot nguong USD.

# Monitor: theo doi chi tieu theo tung dich vu (SERVICE)
resource "aws_ce_anomaly_monitor" "this" {
  name              = "${var.name}-monitor"
  monitor_type      = "DIMENSIONAL"
  monitor_dimension = "SERVICE"
}

# Subscription: ngưỡng + nơi nhận canh bao (email)
resource "aws_ce_anomaly_subscription" "this" {
  name             = "${var.name}-subscription"
  frequency        = "DAILY"
  monitor_arn_list = [aws_ce_anomaly_monitor.this.arn]

  subscriber {
    type    = "EMAIL"
    address = var.alert_email
  }

  # Chi canh bao khi tac dong tuyet doi cua anomaly >= threshold_usd
  threshold_expression {
    dimension {
      key           = "ANOMALY_TOTAL_IMPACT_ABSOLUTE"
      values        = [tostring(var.threshold_usd)]
      match_options = ["GREATER_THAN_OR_EQUAL"]
    }
  }
}
