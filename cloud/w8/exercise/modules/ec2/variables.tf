variable "name" {
  type = string
}

variable "vpc_id" {
  type = string
}

variable "subnet_id" {
  type        = string
  description = "Public subnet ID for the web server"
}

variable "instance_type" {
  type    = string
  default = "t3.micro" # free tier
}
