# W10 — Day A: RBAC + Admission Policy

Scope D1: RBAC (3 role `viewer`/`developer`/`sre` + ServiceAccount +
`kubectl auth can-i`), OPA/Gatekeeper (ConstraintTemplate vs Constraint, Rego),
ValidatingAdmissionPolicy native (K8s 1.30+), audit mode vs enforce.
Tài liệu nền: [`knowledge/w10-foundation-rbac-secrets-platform.md`](../../../knowledge/w10-foundation-rbac-secrets-platform.md) §1–§6.

Tinh thần: chặn vi phạm **ở cluster level**, không dựa "developer hứa". RBAC =
*ai được làm gì*; Admission Policy = *cái gì được vào cluster*.

## Layout

```
day-a/
  README.md
  notes.md                    Ghi chú self-study D1
  EVIDENCE_PACK.md            Tổng hợp bằng chứng (screenshot + log)
  screenshots/
  rbac/
    00-namespace.yaml         ns w10-demo + 3 ServiceAccount
    viewer.yaml               Role read-only + RoleBinding
    developer.yaml            Role quản workload + RoleBinding
    sre.yaml                  ClusterRole cross-ns + ClusterRoleBinding
    test-can-i.ps1            Kiểm chứng ma trận quyền bằng impersonation
  policies/
    install.md                Cài Gatekeeper + thứ tự apply
    templates/                4 ConstraintTemplate (Rego)
    constraints/              4 Constraint (3 deny + 1 dryrun)
    vap/                      ValidatingAdmissionPolicy native (CEL)
    test/                     bad-pod (deny) + good-pod (pass) + audit-root-pod (dryrun)
```

CI: `.github/workflows/validate-w10-day-a.yml` chạy kubeconform khi mở PR.

## Mục tiêu D1 (acceptance)

| # | Yêu cầu | Artifact |
|---|---|---|
| 1 | 3 role rõ ràng `viewer`/`developer`/`sre` | `rbac/*.yaml` |
| 2 | Chứng minh phân quyền bằng `auth can-i` | `rbac/test-can-i.ps1` |
| 3 | 4 Gatekeeper constraint (3 enforce + 1 audit) | `policies/templates` + `policies/constraints` |
| 4 | Hiểu ConstraintTemplate vs Constraint | `policies/templates` + `policies/constraints` + foundation §4 |
| 5 | VAP native + so sánh với Gatekeeper | `policies/vap/` + foundation §5 |
| 6 | Audit mode vs enforce | `constraints/require-nonroot.yaml` (dryrun) |

> "foundation" = [`knowledge/w10-foundation-rbac-secrets-platform.md`](../../../knowledge/w10-foundation-rbac-secrets-platform.md).

## Run

```powershell
minikube start --cpus=2 --memory=4000 --driver=docker

# RBAC
kubectl apply -f cloud/w10/day-a/rbac/
.\cloud\w10\day-a\rbac\test-can-i.ps1

# Gatekeeper (chi tiết: policies/install.md)
kubectl apply --server-side --force-conflicts `
  -f https://raw.githubusercontent.com/open-policy-agent/gatekeeper/release-3.17/deploy/gatekeeper.yaml
kubectl -n gatekeeper-system rollout status deploy/gatekeeper-controller-manager
kubectl apply -f cloud/w10/day-a/policies/templates/
Start-Sleep -Seconds 10   # đợi CRD từ template sẵn sàng
kubectl apply -f cloud/w10/day-a/policies/constraints/
kubectl apply -f cloud/w10/day-a/policies/vap/

# Demo
kubectl apply -f cloud/w10/day-a/policies/test/bad-pod.yaml        # deny
kubectl apply -f cloud/w10/day-a/policies/test/good-pod.yaml       # admit + Running
kubectl apply -f cloud/w10/day-a/policies/test/audit-root-pod.yaml # admit (rule dryrun)
kubectl get constraints
```

Bằng chứng: `EVIDENCE_PACK.md`. Bẫy khi chạy thật + cluster RAM thấp: `notes.md` §7–§8.
