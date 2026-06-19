resource "aws_macie2_account" "this" {
  finding_publishing_frequency = "FIFTEEN_MINUTES"
  status                       = "ENABLED"
}

resource "time_sleep" "macie_slr" {
  depends_on      = [aws_macie2_account.this]
  create_duration = "180s"
}

resource "aws_macie2_classification_job" "scan" {
  name     = "${var.name}-scan"
  job_type = "ONE_TIME"

  s3_job_definition {
    bucket_definitions {
      account_id = data.aws_caller_identity.current.account_id
      buckets    = [aws_s3_bucket.data.id]
    }
  }

  depends_on = [
    time_sleep.macie_slr,
    aws_s3_object.samples,
  ]
}
