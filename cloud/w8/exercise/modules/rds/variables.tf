variable "name" {
  type = string
}

variable "vpc_id" {
  type = string
}

variable "private_subnet_ids" {
  type        = list(string)
  description = "Private subnet IDs for the DB subnet group"
}

variable "web_security_group_id" {
  type        = string
  description = "Web security group allowed to connect to MySQL"
}

variable "db_name" {
  type    = string
  default = "appdb"
}

variable "db_username" {
  type    = string
  default = "admin"
}

variable "db_password" {
  type        = string
  description = "Database password. Pass through tfvars or environment variable."
  sensitive   = true
}

variable "instance_class" {
  type    = string
  default = "db.t3.micro"
}
