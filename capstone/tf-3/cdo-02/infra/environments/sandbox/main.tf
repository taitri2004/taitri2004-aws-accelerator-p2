provider "aws" {
  region = var.region
  default_tags {
    tags = var.tags
  }
}

module "networking" {
  source = "../../modules/networking"

  name     = var.name
  vpc_cidr = var.vpc_cidr
  azs      = var.azs
  tags     = var.tags
}

module "eks" {
  source = "../../modules/eks"

  name               = var.name
  cluster_version    = var.cluster_version
  vpc_id             = module.networking.vpc_id
  private_subnet_ids = module.networking.private_subnet_ids
  tags               = var.tags
}

module "state_audit" {
  source = "../../modules/state-audit"

  name                 = var.name
  audit_retention_days = var.audit_retention_days
  tags                 = var.tags
}

# ---------------------------------------------------------------------------
# STAGE 2 — tenant provisioning (chạy SAU khi cluster up).
# Kubernetes provider cần cluster đã tồn tại → tách stage để base apply không vỡ.
# Bỏ comment sau `terraform apply` stage 1 + `aws eks update-kubeconfig`.
# ---------------------------------------------------------------------------
# provider "kubernetes" {
#   host                   = module.eks.cluster_endpoint
#   cluster_ca_certificate = base64decode(module.eks.cluster_ca)
#   exec {
#     api_version = "client.authentication.k8s.io/v1beta1"
#     command     = "aws"
#     args        = ["eks", "get-token", "--cluster-name", module.eks.cluster_name, "--region", var.region]
#   }
# }
#
# module "tenant_a" {
#   source     = "../../modules/tenant-provision"
#   tenant_id  = "tnt-a"
#   namespace  = "onlineboutique-tnt-a"
#   audit_bucket = module.state_audit.audit_bucket
# }
#
# module "tenant_b" {
#   source     = "../../modules/tenant-provision"
#   tenant_id  = "tnt-b"
#   namespace  = "onlineboutique-tnt-b"
#   audit_bucket = module.state_audit.audit_bucket
# }
