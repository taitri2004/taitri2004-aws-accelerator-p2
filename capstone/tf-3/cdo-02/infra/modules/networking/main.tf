locals {
  private_subnets = [for i, az in var.azs : cidrsubnet(var.vpc_cidr, 4, i)]     # 10.0.0.0/20, 10.0.16.0/20
  public_subnets  = [for i, az in var.azs : cidrsubnet(var.vpc_cidr, 4, i + 8)] # 10.0.128.0/20, ...
}

module "vpc" {
  source  = "terraform-aws-modules/vpc/aws"
  version = "~> 5.8"

  name = "${var.name}-vpc"
  cidr = var.vpc_cidr
  azs  = var.azs

  private_subnets = local.private_subnets
  public_subnets  = local.public_subnets

  enable_nat_gateway   = true
  single_nat_gateway   = true # cost saving cho sandbox (giảm HA, chấp nhận)
  enable_dns_hostnames = true
  enable_dns_support   = true

  # Tag cho EKS auto-discovery (ELB / internal-elb)
  public_subnet_tags  = { "kubernetes.io/role/elb" = "1" }
  private_subnet_tags = { "kubernetes.io/role/internal-elb" = "1" }

  tags = var.tags
}

# VPC endpoints: traffic private, không ra Internet (deployment contract §6)
module "vpc_endpoints" {
  source  = "terraform-aws-modules/vpc/aws//modules/vpc-endpoints"
  version = "~> 5.8"

  vpc_id = module.vpc.vpc_id

  endpoints = {
    s3 = {
      service         = "s3"
      service_type    = "Gateway"
      route_table_ids = module.vpc.private_route_table_ids
    }
    dynamodb = {
      service         = "dynamodb"
      service_type    = "Gateway"
      route_table_ids = module.vpc.private_route_table_ids
    }
    secretsmanager = {
      service             = "secretsmanager"
      private_dns_enabled = true
      subnet_ids          = module.vpc.private_subnets
      security_group_ids  = [aws_security_group.endpoints.id]
    }
    bedrock_runtime = {
      service             = "bedrock-runtime"
      private_dns_enabled = true
      subnet_ids          = module.vpc.private_subnets
      security_group_ids  = [aws_security_group.endpoints.id]
    }
  }

  tags = var.tags
}

resource "aws_security_group" "endpoints" {
  name_prefix = "${var.name}-vpce-"
  vpc_id      = module.vpc.vpc_id

  ingress {
    description = "HTTPS from within VPC"
    from_port   = 443
    to_port     = 443
    protocol    = "tcp"
    cidr_blocks = [var.vpc_cidr]
  }

  tags = var.tags
}
