# variables.tf — root module

variable "region" {
  type        = string
  description = "AWS region"
  default     = "ap-southeast-1"
}
