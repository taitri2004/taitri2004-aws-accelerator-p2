# Stage-2: provision 1 tenant = 1 namespace + RBAC least-privilege + NetworkPolicy deny-all.
# Khớp deployment contract §3.D (1 controller SA tf3-cdo-controller, Role per-ns) + ADR-002 (namespace-per-tenant).
# Cần kubernetes provider đã config (cluster up).

terraform {
  required_providers {
    kubernetes = {
      source  = "hashicorp/kubernetes"
      version = "~> 2.27"
    }
  }
}

resource "kubernetes_namespace" "tenant" {
  metadata {
    name = var.namespace
    labels = {
      tenant_id                            = var.tenant_id
      "istio-injection"                    = "enabled" # Istio sidecar (ADR-003)
      "pod-security.kubernetes.io/enforce" = "restricted"
    }
  }
}

# §3.D: KHÔNG tạo SA per-tenant. CDO controller dùng 1 ServiceAccount `tf3-cdo-controller`
# (ns platform, khai báo ở manifests/platform/executor.yaml), được bind per-namespace bên dưới.

# Role least-privilege per-namespace — verb tối thiểu đúng deployment-contract §3.D
resource "kubernetes_role" "executor" {
  metadata {
    name      = "tf3-cdo-executor-role"
    namespace = kubernetes_namespace.tenant.metadata[0].name
  }

  rule {
    api_groups = ["apps"]
    resources  = ["deployments"]
    verbs      = ["get", "list", "patch"] # KHÔNG delete (chỉ patch/rollback)
  }
  rule {
    api_groups = ["apps"]
    resources  = ["deployments/scale"]
    verbs      = ["get", "patch"] # SCALE_REPLICAS
  }
  rule {
    api_groups = ["apps"]
    resources  = ["replicasets"]
    verbs      = ["get", "list"] # revision cho ROLLOUT_UNDO
  }
  rule {
    api_groups = [""]
    resources  = ["pods"]
    verbs      = ["get", "list", "patch"] # KHÔNG delete (DELETE_POD bị cấm)
  }
  rule {
    api_groups = [""]
    resources  = ["pods/log"]
    verbs      = ["get"] # thu telemetry xác thực
  }
  rule {
    api_groups = [""]
    resources  = ["secrets"]
    verbs      = ["get", "create", "delete"] # CHỈ ROTATE_SECRET
  }
}

resource "kubernetes_role_binding" "executor" {
  metadata {
    name      = "tf3-cdo-executor-binding"
    namespace = kubernetes_namespace.tenant.metadata[0].name
  }
  role_ref {
    api_group = "rbac.authorization.k8s.io"
    kind      = "Role"
    name      = kubernetes_role.executor.metadata[0].name
  }
  subject {
    kind      = "ServiceAccount"
    name      = "tf3-cdo-controller" # 1 controller SA (ns platform) — §3.D
    namespace = "platform"
  }
}

# NetworkPolicy deny-all default + allow intra-namespace (chặn cross-tenant)
resource "kubernetes_network_policy" "deny_all" {
  metadata {
    name      = "deny-all-default"
    namespace = kubernetes_namespace.tenant.metadata[0].name
  }
  spec {
    pod_selector {}
    policy_types = ["Ingress", "Egress"]

    ingress {
      from {
        namespace_selector {
          match_labels = { tenant_id = var.tenant_id }
        }
      }
    }
    egress {
      to {
        namespace_selector {
          match_labels = { tenant_id = var.tenant_id }
        }
      }
    }
    # DNS egress
    egress {
      ports {
        port     = "53"
        protocol = "UDP"
      }
    }
  }
}

# ResourceQuota chống noisy neighbor
resource "kubernetes_resource_quota" "tenant" {
  metadata {
    name      = "tenant-quota"
    namespace = kubernetes_namespace.tenant.metadata[0].name
  }
  spec {
    hard = {
      "requests.cpu"    = "2"
      "requests.memory" = "4Gi"
      "limits.cpu"      = "4"
      "limits.memory"   = "8Gi"
    }
  }
}
