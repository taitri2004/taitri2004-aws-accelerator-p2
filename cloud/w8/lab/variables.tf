variable "region" {
  type        = string
  description = "AWS region"
  default     = "ap-southeast-1"
}

variable "name" {
  type        = string
  description = "Name prefix and app display name"
  default     = "w8-lab"
}

variable "vpc_cidr" {
  type        = string
  description = "CIDR cho custom VPC"
  default     = "10.0.0.0/16"
}

variable "instance_type" {
  type        = string
  description = "EC2 instance type"
  default     = "t3.medium"
}

variable "node_port" {
  type        = number
  description = "Kubernetes Service NodePort exposed on the EC2 host"
  default     = 30080

  validation {
    condition     = var.node_port >= 30000 && var.node_port <= 32767
    error_message = "node_port phải nằm trong dải 30000-32767."
  }
}
