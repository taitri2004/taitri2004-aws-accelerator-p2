variable "region" {
  type    = string
  default = "ap-southeast-1"
}

variable "state_bucket_name" {
  type        = string
  description = "Globally unique bucket name for Terraform state"
  default     = "taitri2004-tfstate-w8"
}
