# variables.tf — input parameters

variable "region" {
  type        = string
  description = "AWS region"
  default     = "ap-southeast-1"
}

variable "bucket_base_name" {
  type        = string
  description = "Phần tên gốc của bucket (sẽ thêm hậu tố ngẫu nhiên)"
  default     = "w8d1-tf-demo"

  # validation: tên bucket S3 chỉ cho chữ thường, số, dấu gạch ngang
  validation {
    condition     = can(regex("^[a-z0-9-]+$", var.bucket_base_name))
    error_message = "bucket_base_name chỉ được chứa chữ thường, số và dấu gạch ngang."
  }
}
