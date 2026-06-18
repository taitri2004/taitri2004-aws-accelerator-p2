# variables.tf
variable "region" {
  description = "Region cho provider. Cost Explorer la global nen dung us-east-1."
  type        = string
  default     = "us-east-1"
}

variable "name" {
  description = "Tien to dat ten resource"
  type        = string
  default     = "w10-platform"
}

variable "alert_email" {
  description = "Email nhan canh bao chi phi bat thuong"
  type        = string
}

variable "threshold_usd" {
  description = "Nguong USD: chi canh bao khi tac dong bat thuong >= gia tri nay"
  type        = number
  default     = 20
}
