# W10 Homework — Phát hiện dữ liệu nhạy cảm trong S3 bằng Amazon Macie → email

Macie quét bucket S3, ra **findings** khi thấy dữ liệu nhạy cảm (SSN, thẻ tín dụng, AWS key...),
EventBridge bắt finding rồi đẩy qua SNS gửi **email** cảnh báo.

## Cấu trúc

```
versions.tf / providers.tf   provider AWS
variables.tf                 region, name, alert_email
s3.tf                        bucket + chặn public + upload sample files
macie.tf                     bật Macie + classification job (ONE_TIME)
alerts.tf                    SNS + email sub + EventBridge rule (Macie Finding) -> SNS
sample-data/                 file mẫu chứa PII GIẢ (để Macie phát hiện)
outputs.tf
```

## Triển khai

Copy `terraform.tfvars.example` thành `terraform.tfvars` và điền email thật, rồi:

```bash
terraform init
terraform apply
```

Sau apply: mở email, bấm "Confirm subscription" (SNS bắt buộc, chưa confirm thì không nhận alert).

## Map vào diagram

| Bước trong diagram | File / resource |
|---|---|
| Upload sample files → S3 Bucket | `aws_s3_bucket.data`, `aws_s3_object.samples` |
| S3 Bucket → Amazon Macie Job | `aws_macie2_account.this`, `aws_macie2_classification_job.scan` |
| Macie → Findings | job chạy xong → findings (xem console/CLI) |
| Rule created for alerts | `aws_cloudwatch_event_rule.macie_finding` |
| EventBridge → SNS → Email | `aws_cloudwatch_event_target.to_sns`, `aws_sns_topic*` |

## Kiểm chứng

Job ONE_TIME chạy vài phút. Theo dõi trạng thái job rồi xem findings:
```bash
aws macie2 describe-classification-job --job-id $(terraform output -raw macie_job_id) --region ap-southeast-1 --query jobStatus
aws macie2 list-findings --region ap-southeast-1
```
Job RUNNING → COMPLETE → có findings → EventBridge → **email cảnh báo** (vài phút sau).

## Dọn

```bash
terraform destroy
```
