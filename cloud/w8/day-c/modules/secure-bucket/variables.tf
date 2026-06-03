# modules/secure-bucket/variables.tf — interface (input) của module

variable "bucket_name" {
  type        = string
  description = "Tên bucket (phải unique toàn cầu)"

  validation {
    condition     = can(regex("^[a-z0-9-]+$", var.bucket_name))
    error_message = "bucket_name chỉ được chứa chữ thường, số và dấu gạch ngang."
  }
}

variable "enable_versioning" {
  type        = bool
  description = "Bật versioning hay không"
  default     = true
}

variable "tags" {
  type        = map(string)
  description = "Tag gắn cho bucket"
  default     = {}
}
