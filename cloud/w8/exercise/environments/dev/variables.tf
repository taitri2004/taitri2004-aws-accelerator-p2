variable "region" {
  type    = string
  default = "ap-southeast-1"
}

variable "name" {
  type    = string
  default = "w8ex"
}

variable "vpc_cidr" {
  type    = string
  default = "10.0.0.0/16"
}

variable "instance_type" {
  type    = string
  default = "t3.micro"
}

variable "db_password" {
  type        = string
  description = "RDS password. Pass through terraform.tfvars or TF_VAR_db_password."
  sensitive   = true
}
