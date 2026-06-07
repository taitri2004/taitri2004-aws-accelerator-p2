variable "name" {
  type        = string
  description = "Resource name prefix"
}

variable "vpc_cidr" {
  type        = string
  description = "VPC CIDR block"
  default     = "10.0.0.0/16"
}
