variable "region" {
  type    = string
  default = "us-east-1"
}

variable "name" {
  type    = string
  default = "tf-3-cdo2-sandbox"
}

variable "cluster_version" {
  type    = string
  default = "1.31" # khớp Client n-1 policy
}

variable "vpc_cidr" {
  type    = string
  default = "10.0.0.0/16"
}

variable "azs" {
  type    = list(string)
  default = ["us-east-1a", "us-east-1b"]
}

variable "audit_retention_days" {
  type    = number
  default = 90 # SOC2 ≥90d
}

variable "tags" {
  type = map(string)
  default = {
    Project   = "tf-3-self-heal"
    Team      = "cdo-2"
    ManagedBy = "terraform"
  }
}
