module "eks" {
  source  = "terraform-aws-modules/eks/aws"
  version = "~> 20.8"

  cluster_name    = var.name
  cluster_version = var.cluster_version

  cluster_endpoint_public_access           = true
  enable_cluster_creator_admin_permissions = true

  # Secrets encryption tại etcd bằng KMS (03_security_design §4.1) — module tự tạo CMK
  cluster_encryption_config = {
    resources = ["secrets"]
  }

  vpc_id     = var.vpc_id
  subnet_ids = var.private_subnet_ids

  # Addon chuẩn cho cluster chạy + observability cơ bản
  cluster_addons = {
    coredns                = {}
    kube-proxy             = {}
    vpc-cni                = {}
    eks-pod-identity-agent = {}
  }

  eks_managed_node_groups = {
    default = {
      instance_types = ["t3.medium"]
      capacity_type  = "SPOT" # cost saving (ADR cost)
      min_size       = 2
      max_size       = 4
      desired_size   = 2
    }
  }

  # IRSA/OIDC provider bật mặc định ở v20 → ServiceAccount executor dùng IRSA (no static key)

  tags = var.tags
}
