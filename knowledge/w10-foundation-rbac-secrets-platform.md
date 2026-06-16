# W10 — Foundation: RBAC + Secrets/Supply Chain + Platform

Kiến thức nền cho W10 "Secure & Operate", tổng hợp từ tài liệu chính thống:
Kubernetes RBAC, OPA/Gatekeeper, ValidatingAdmissionPolicy, External Secrets
Operator, Cosign/Sigstore, Trivy, SLSA.

Tinh thần W10: chặn vi phạm **ở cluster level** (admission control), không dựa
"developer hứa". RBAC trả lời *ai được làm gì*; Admission Policy trả lời *cái gì
được phép vào cluster*.

## Map nội dung

| Ngày | Chủ đề | Section |
|---|---|---|
| D1 | RBAC + Admission Policy | §1 RBAC · §2 ServiceAccount · §3 `auth can-i` · §4 OPA/Gatekeeper · §5 VAP native · §6 audit vs enforce |
| D2 | Secrets + Supply Chain | (bổ sung T3 16/06) |
| D3 | Platform Integration + Cost | (bổ sung T4 17/06) |
| Lab | 6-risk cleanup + enforcement | (onsite T5–T6) |

> File này hiện viết đầy đủ phần **D1**. D2/D3 sẽ nối thêm section đúng ngày.

---

## §1. RBAC — bốn object cốt lõi

RBAC (Role-Based Access Control) trong K8s ghép **subject** với **quyền** qua
bốn loại object:

| Object | Phạm vi | Vai trò |
|---|---|---|
| `Role` | 1 namespace | Tập rule (apiGroups + resources + verbs) trong namespace |
| `ClusterRole` | toàn cluster | Tập rule cluster-wide (nodes, PV) hoặc tái dùng nhiều ns |
| `RoleBinding` | 1 namespace | Gắn Role/ClusterRole vào subject **trong namespace đó** |
| `ClusterRoleBinding` | toàn cluster | Gắn ClusterRole vào subject **mọi namespace** |

Quy tắc quan trọng:
- RBAC là **additive** — không có rule "deny". Mặc định cấm; chỉ cộng quyền.
- Một `RoleBinding` có thể trỏ tới `ClusterRole` → tái dùng một định nghĩa
  quyền cho nhiều namespace (vd ClusterRole `view` built-in).
- `verbs` thường gặp: `get list watch` (đọc), `create update patch delete`
  (ghi), `*` (mọi verb). Sub-resource: `pods/log`, `pods/exec`.

Ba role chuẩn W10 (mục tiêu cuối tuần):

| Role | Ý nghĩa | Phạm vi |
|---|---|---|
| `viewer` | read-only, audit/onboarding | namespace (Role) |
| `developer` | quản workload trong namespace của mình, không sờ RBAC/namespace | namespace (Role) |
| `sre` | vận hành cross-namespace, xem node, quản Gatekeeper constraint | cluster (ClusterRole) |

## §2. ServiceAccount — danh tính cho workload & test

- **User/Group**: K8s không có DB user; user đến từ certificate/OIDC, group từ
  claim. Dùng cho con người.
- **ServiceAccount (SA)**: danh tính *trong cluster* gắn vào pod. Pod mặc định
  mount token của SA `default` trong namespace.
- Subject của binding có 3 `kind`: `User`, `Group`, `ServiceAccount`.

Tên đầy đủ của một SA dùng khi impersonate:
`system:serviceaccount:<namespace>:<sa-name>`.

Best practice (khớp live IRSA): pod **không** dùng static AWS key. Trên EKS, gắn
SA với IAM role qua **IRSA** (annotation `eks.amazonaws.com/role-arn`), pod lấy
credential tạm qua OIDC. → SA vừa là danh tính RBAC trong cluster, vừa là cầu
nối IAM ngoài cluster.

## §3. `kubectl auth can-i` — kiểm chứng quyền

Cách kiểm tra RBAC mà không cần đăng nhập thật:

```bash
# Tôi có xoá được pod trong ns hiện tại không?
kubectl auth can-i delete pods

# Impersonate một ServiceAccount
kubectl auth can-i list deployments \
  --as=system:serviceaccount:w10-demo:developer -n w10-demo

# Impersonate một Group
kubectl auth can-i create clusterrolebindings --as-group=developers --as=alice

# Liệt kê toàn bộ quyền của một SA
kubectl auth can-i --list \
  --as=system:serviceaccount:w10-demo:sre
```

`--as` / `--as-group` cần chính bạn có quyền `impersonate` (admin có sẵn). Đây là
công cụ chính để chứng minh "developer KHÔNG xoá được namespace" trong evidence.

## §4. OPA / Gatekeeper — admission policy

RBAC kiểm soát *ai*, nhưng không chặn được "developer hợp lệ deploy image
`:latest` không set resource limit". Cần **admission controller** soi mọi object
trước khi nó vào cluster.

**Gatekeeper** = OPA chạy như Validating Admission Webhook, viết policy bằng
**Rego**. Hai object:

| Object | Vai trò | Ví dụ |
|---|---|---|
| `ConstraintTemplate` | định nghĩa *logic* (Rego) + schema tham số, sinh ra một CRD mới | `K8sRequiredLabels` |
| Constraint (instance của CRD đó) | *áp dụng* template với tham số + `match` + `enforcementAction` | "Namespace phải có label `team`" |

Một template viết một lần, nhiều constraint tái dùng với tham số khác nhau.

Cấu trúc Rego trong template (target `admission.k8s.gatekeeper.sh`):

```rego
package k8srequiredlabels
violation[{"msg": msg}] {
  required := input.parameters.labels            # tham số từ constraint
  provided := {l | input.review.object.metadata.labels[l]}
  missing := required - provided                 # phép trừ set
  count(missing) > 0
  msg := sprintf("missing required labels: %v", [missing])
}
```

- `input.review.object` = object đang được admit.
- `input.parameters` = `spec.parameters` của constraint.
- Mỗi `violation` thoả → request bị từ chối (nếu enforce).

**Kyverno** là alternative (YAML thay vì Rego, dễ đọc hơn cho người mới). W10
dùng Gatekeeper theo yêu cầu chương trình; Kyverno để tham khảo cho phần verify
image signature ở D2.

Bốn constraint chuẩn W10 (mục tiêu cuối tuần — 4 enforce):
1. **Required labels** — namespace/workload phải có label `team`.
2. **Block `:latest` tag** — cấm image không pin tag.
3. **Required resources** — container phải set cpu/memory limit.
4. **Run as non-root** — pod/container phải `runAsNonRoot: true`.

## §5. ValidatingAdmissionPolicy (VAP) — native K8s 1.30+

Từ K8s 1.30, admission policy có thể viết **không cần webhook ngoài**, dùng
**CEL** (Common Expression Language) ngay trong API server:

| Object | Vai trò |
|---|---|
| `ValidatingAdmissionPolicy` | định nghĩa `validations` bằng biểu thức CEL |
| `ValidatingAdmissionPolicyBinding` | gắn policy vào scope (namespace selector) + chọn `validationActions` |

```yaml
validations:
  - expression: "object.spec.containers.all(c, has(c.resources.limits))"
    message: "every container must set resource limits"
```

So sánh nhanh:

| | Gatekeeper (OPA) | VAP native |
|---|---|---|
| Engine | Webhook ngoài + Rego | API server + CEL |
| Cài đặt | Phải deploy Gatekeeper | Built-in (1.30+) |
| Sức mạnh | Rất linh hoạt (data, external) | Đủ cho validate đơn giản |
| Khi nào | Policy phức tạp, audit, mutation | Validate nhẹ, không muốn thêm webhook |

W10 dùng **cả hai** để hiểu trade-off: Gatekeeper cho 4 constraint chính, VAP
native cho một policy resource-limit minh hoạ.

## §6. Audit mode vs Enforce

`enforcementAction` của constraint (Gatekeeper) / `validationActions` (VAP):

| Mode | Gatekeeper | VAP | Hành vi |
|---|---|---|---|
| Enforce | `deny` | `Deny` | Từ chối request vi phạm |
| Audit | `dryrun` | `Audit` | Cho qua, ghi vi phạm vào status/event |
| Cảnh báo | `warn` | `Warn` | Cho qua, trả warning cho client |

Quy trình rollout policy an toàn (tránh chặn nhầm production):
1. Bắt đầu ở **audit** (`dryrun`/`Audit`) → xem `kubectl get constraint` field
   `status.totalViolations` để biết bao nhiêu workload đang vi phạm.
2. Sửa workload vi phạm.
3. Khi violation = 0 → chuyển sang **enforce** (`deny`/`Deny`).

→ Đây là lý do D1 để một constraint (`require-nonroot`) ở `dryrun` minh hoạ
audit, ba constraint còn lại `deny`. Cuối tuần flip tất cả sang enforce.

---

## Tài liệu nguồn (D1)

- Kubernetes RBAC — https://kubernetes.io/docs/reference/access-authn-authz/rbac
- OPA / Rego — https://www.openpolicyagent.org/docs
- Gatekeeper — https://open-policy-agent.github.io/gatekeeper
- ValidatingAdmissionPolicy — https://kubernetes.io/docs/reference/access-authn-authz/validating-admission-policy
- Kyverno — https://kyverno.io/docs
- EKS Best Practices (RBAC/IRSA) — https://aws.github.io/aws-eks-best-practices/security/docs
