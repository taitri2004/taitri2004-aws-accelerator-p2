variable "region" {
  type        = string
  description = "AWS region"
  default     = "ap-southeast-1"
}

variable "name" {
  type        = string
  description = "Name prefix for resources"
  default     = "w9-monitoring"
}

variable "instance_type" {
  type        = string
  description = "EC2 instance type"
  default     = "t3.micro"
}

variable "alert_email" {
  type        = string
  description = "Email nhan alert qua SNS (xac nhan qua link trong mail)"
}
