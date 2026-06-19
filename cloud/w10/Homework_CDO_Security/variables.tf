variable "region" {
  type        = string
  description = "AWS region (Macie phai duoc ho tro o region nay)"
  default     = "ap-southeast-1"
}

variable "name" {
  type        = string
  description = "Name prefix cho resources (dung lam ten bucket -> chu thuong, khong gach duoi)"
  default     = "w10-cdo-security"
}

variable "alert_email" {
  type        = string
  description = "Email nhan canh bao Macie qua SNS (phai bam Confirm trong mail)"
}
