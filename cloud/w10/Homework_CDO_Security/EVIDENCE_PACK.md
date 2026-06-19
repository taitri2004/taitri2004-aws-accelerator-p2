# Evidence Pack - Macie CDO Security

Dien khi chay that (dinh kem anh vao screenshots/).

| # | Bang chung | Lenh / noi xem | Trang thai |
|---|---|---|---|
| 1 | Macie da bat | `aws macie2 get-macie-session --query status` -> ENABLED | DONE |
| 2 | Sample files tren S3 | `aws s3 ls s3://<bucket>` -> customers.csv, employee-notes.txt | DONE |
| 3 | Classification job chay | `describe-classification-job` -> RUNNING/COMPLETE (numberOfRuns=1) | DONE |
| 4 | Findings (sensitive data) | 2 findings High - xem duoi | DONE |
| 5 | EventBridge rule | `w10-cdo-security-macie-finding` (source aws.macie, "Macie Finding") | DONE |
| 6 | SNS subscription confirmed | ARN that, khac PendingConfirmation | DONE |
| 7 | Email canh bao nhan duoc | 2 mail "[Macie] phat hien du lieu nhay cam..." -> screenshots/ | DONE |

## Ket qua that (run 2026-06-19, region ap-southeast-1)
- Job id: b231d80cece043cc2510fdef3b0e8949
- Bucket: w10-cdo-security-749043157095
- So findings: 2 (deu severity High)
  - customers.csv -> SensitiveData:S3Object/Multiple -> CREDIT_CARD_NUMBER + USA_SOCIAL_SECURITY_NUMBER
  - employee-notes.txt -> SensitiveData:S3Object/Personal -> USA_SOCIAL_SECURITY_NUMBER
- SNS topic: arn:aws:sns:ap-southeast-1:749043157095:w10-cdo-security-macie-alerts (subscription confirmed)
