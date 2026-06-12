# W9 Homework — CloudWatch CPU Alarm → Email via SNS

## Cấu trúc

```
versions.tf / providers.tf   provider AWS
variables.tf                 region, name, instance_type, alert_email
iam.tf                       role EC2 + CloudWatchAgentServerPolicy + SSM
compute.tf                   EC2 AL2023 + user_data cài/chạy agent
monitoring.tf                SNS topic + email sub + CPU alarm
templates/                   cw_agent_config.json (memory), user_data.sh.tftpl
outputs.tf
```

## Triển khai

```bash
cp terraform.tfvars.example terraform.tfvars   # điền email thật
terraform init
terraform apply
```

Sau apply: **mở email → bấm "Confirm subscription"** (SNS bắt buộc, chưa confirm thì không nhận alert).

## Map vào slide

| Slide | File / resource |
|---|---|
| S03-1 SNS topic + email sub | `aws_sns_topic.alerts`, `aws_sns_topic_subscription.email` |
| S03-2 Alarm EC2 CPUUtilization | `aws_cloudwatch_metric_alarm.cpu_high` |
| S03-3 > 80%, 5 phút, 1/1 datapoint | `threshold=80`, `period=300`, `evaluation_periods=1` |
| S03-4 Alarm → SNS (+ OK recovery) | `alarm_actions`, `ok_actions` |
| S02 cài/chạy agent + IAM prereq | `compute.tf`, `iam.tf` |

## Kiểm chứng

Đẩy CPU > 80% qua SSM rồi đợi alarm fire:
```bash
aws ssm start-session --target <instance_id> --region ap-southeast-1
for i in $(seq $(nproc)); do yes > /dev/null & done   # CPU 100%
# để chạy > 5 phút -> email "ALARM"
pkill yes                                              # CPU tụt -> email "OK"
```

Agent chạy chưa:
```bash
sudo /opt/aws/amazon-cloudwatch-agent/bin/amazon-cloudwatch-agent-ctl -m ec2 -a status
```

## Dọn

```bash
terraform destroy
```
