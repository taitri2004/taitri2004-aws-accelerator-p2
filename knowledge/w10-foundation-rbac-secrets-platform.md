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
| D2 | Secrets + Supply Chain | §7 ESO + Secrets Manager · §8 rotation no-restart · §9 Trivy CI · §10 Cosign/Sigstore · §11 verify signature · §12 exception CVE |
| D3 | Platform Integration + Cost | §13 tích hợp W8→W10 · §14 ResourceQuota + LimitRange · §15 chaos test · §16 runbook · §17 Cost Anomaly Detection |
| Lab | 6-risk cleanup + enforcement | (onsite T5–T6) |

> File này hiện viết đầy đủ **D1 + D2 + D3**.

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

## §7. External Secrets Operator (ESO) + AWS Secrets Manager

Vấn đề: secret không nên nằm trong Git (kể cả Sealed Secrets vẫn phải commit
ciphertext). ESO đảo hướng: **nguồn sự thật là một secret store ngoài** (AWS
Secrets Manager, Vault, GCP SM...), ESO pull về và **sinh ra `Secret` của K8s**.

Ba object:

| Object | Vai trò |
|---|---|
| `SecretStore` / `ClusterSecretStore` | Khai báo provider + cách auth (vd AWS SM, region, IRSA) |
| `ExternalSecret` | "Lấy key X từ store, ghi vào `Secret` Y", có `refreshInterval` |
| `Secret` (do ESO tạo) | Secret K8s bình thường, workload dùng như thường |

```yaml
kind: ExternalSecret
spec:
  refreshInterval: 15s            # ESO poll store mỗi 15s
  secretStoreRef: { name: aws-secrets, kind: ClusterSecretStore }
  target: { name: app-secret }    # tên Secret K8s sinh ra
  data:
    - secretKey: db-password       # key trong Secret K8s
      remoteRef: { key: prod/app, property: db_password }  # trong AWS SM
```

Auth trên EKS = **IRSA** (ServiceAccount gắn IAM role), không nhét access key.
Local/offline có thể dùng provider `fake` (giá trị inline) để demo cơ chế.

## §8. Rotation < 60s, không restart pod

Yêu cầu W10: đổi secret ở store → workload thấy giá trị mới trong < 60s mà
**không restart**. Mấu chốt là cách workload đọc secret:

| Cách dùng secret | Cập nhật khi Secret đổi? |
|---|---|
| `env` / `envFrom` (biến môi trường) | **Không** — phải restart pod |
| Volume mount (file) | **Có** — kubelet tự refresh file trong pod |

→ Để rotation no-restart: mount Secret dạng **volume** (file), app đọc lại file.
Chuỗi: rotate ở store → ESO sync (`refreshInterval`) cập nhật Secret K8s →
kubelet cập nhật file mount → app đọc giá trị mới. Tổng độ trễ ≈ refreshInterval
+ chu kỳ sync của kubelet (vài chục giây). Dùng `refreshInterval: 10s` cho demo.

## §9. Trivy — quét image trong CI

Trivy quét image tìm CVE (OS packages + app deps), secret lộ, misconfig. Trong
CI đặt **fail-on HIGH/CRITICAL** để chặn build có lỗ hổng nghiêm trọng:

```bash
trivy image --severity HIGH,CRITICAL --exit-code 1 --ignore-unfixed myimg:tag
```

- `--exit-code 1`: có CVE khớp → fail job.
- `--ignore-unfixed`: bỏ qua CVE chưa có bản vá (giảm nhiễu).
- `.trivyignore`: danh sách CVE được miễn **có thời hạn** (ghi rõ ngày + lý do).

## §10. Cosign / Sigstore — ký image

Cosign ký digest của image, lưu chữ ký cạnh image trong registry (OCI artifact).
Hai chế độ:

| | Keyless (OIDC) | Key-based |
|---|---|---|
| Khoá | Không giữ khoá; ký bằng danh tính OIDC (GitHub Actions token), cert ngắn hạn từ Fulcio, log vào Rekor | Cặp khoá `cosign.key`/`cosign.pub` |
| Hợp với | CI/CD (GitHub OIDC), audit công khai | Offline, không muốn phụ thuộc Sigstore public |
| Verify theo | issuer + subject (vd repo + workflow) | public key |

```bash
# keyless (CI): COSIGN_EXPERIMENTAL=1, danh tính từ OIDC
cosign sign myimg@sha256:...
# key-based
cosign generate-key-pair
cosign sign --key cosign.key myimg@sha256:...
```

## §11. Verify signature ở admission

Câu hỏi "verify ở đâu" (CI vs registry vs admission): **admission là chốt cuối**
— dù ai push gì vào registry, cluster chỉ chạy image có chữ ký hợp lệ.

Dùng **Kyverno** `verifyImages` (Gatekeeper không verify chữ ký gọn bằng):

```yaml
kind: ClusterPolicy
spec:
  validationFailureAction: Enforce
  rules:
    - name: verify-signature
      match: { any: [{ resources: { kinds: [Pod] } }] }
      verifyImages:
        - imageReferences: ["ghcr.io/org/*"]
          attestors:
            - entries:
                - keyless:                       # hoặc key: {publicKeys: ...}
                    issuer: https://token.actions.githubusercontent.com
                    subject: https://github.com/org/repo/.github/workflows/*
```

Image không có chữ ký khớp → admission **reject** (đáp ứng acceptance W10).

## §12. Exception policy CVE (có thời hạn)

Đôi khi CVE chưa vá nhưng phải ship. Exception phải **có chủ, có hạn, có lý do**,
không phải tắt vĩnh viễn:

- Trivy: dòng trong `.trivyignore` kèm comment ngày hết hạn + owner.
- Kyverno: `PolicyException` giới hạn đúng resource/namespace.
- ADR ghi quyết định: CVE nào, vì sao chấp nhận, review lại khi nào.

SLSA (supply chain levels) là khung trưởng thành: từ "có provenance" (L1) tới
"build cô lập, không giả mạo được" (L3+). Trivy + Cosign + verify-at-admission là
các mảnh ghép tiến lên SLSA cao hơn.

## §13. Platform integration — ghép W8 → W10

Mục tiêu cuối W10: từ repo dựng **mini platform end-to-end lên fresh cluster
trong < 2h**. Các lớp xếp chồng:

| Lớp | Tuần | Thành phần |
|---|---|---|
| Hạ tầng | W8 | VPC, EKS/cluster, IaC (Terraform) |
| Delivery | W9 | ArgoCD (GitOps) + Prometheus/Grafana (obs) + Argo Rollouts (canary) |
| Bảo mật | W10 | RBAC 3 role + Gatekeeper 4 constraint + ESO + verify signature |
| Guardrail | W10-D3 | ResourceQuota + LimitRange + runbook + cost anomaly |

Thứ tự bootstrap (mỗi lớp là tiền đề lớp sau): cluster → ArgoCD → app-of-apps kéo
toàn bộ (obs, canary, security policy) → namespace + quota/limit → smoke test.
ArgoCD biến "deploy platform" thành "apply một root app", nên thời gian dựng lại
chủ yếu là chờ image pull + reconcile.

## §14. ResourceQuota + LimitRange — guardrail tài nguyên

Hai cơ chế bổ sung nhau, chặn "một team ăn hết cluster":

| | ResourceQuota | LimitRange |
|---|---|---|
| Phạm vi | Tổng cả namespace | Từng container/pod |
| Chặn gì | Tổng cpu/mem/số pod/số secret... vượt hạn mức | Container không set request/limit, hoặc set quá to/nhỏ |
| Hệ quả | Pod thứ N vượt quota bị từ chối | Container thiếu request/limit được **gán default**, hoặc bị reject nếu ngoài min/max |

Quan trọng: khi đã có ResourceQuota cho cpu/memory, **mọi pod buộc phải set
request/limit** nếu không sẽ bị từ chối → LimitRange cấp default để pod cũ không
vỡ. Đây là "cost guard" ở tầng cluster, khớp với Gatekeeper `require-resources`
của D1 (admission) — quota là hạn mức tổng, constraint là bắt buộc khai báo.

## §15. Chaos engineering — kiểm thử khả năng phục hồi

Chaos = cố tình gây lỗi để chứng minh hệ thống tự hồi. Bài cơ bản: xoá pod →
Deployment/ReplicaSet tạo lại; với GitOps thì ArgoCD self-heal kéo về desired;
với canary thì metric xấu auto-abort. Công cụ: Litmus/Chaos Mesh (CRD experiment)
hoặc đơn giản `kubectl delete pod` + quan sát. Nguyên tắc: có giả thuyết ("xoá 1
pod, service vẫn 200"), có steady-state metric để so trước/sau, blast radius nhỏ.

## §16. Runbook — quy trình xử lý sự cố

Runbook = checklist hành động cho một sự cố cụ thể, để người trực làm theo mà
không phải nghĩ lại từ đầu lúc 3h sáng. Khác postmortem (viết SAU sự cố để học).
Cấu trúc runbook: Triệu chứng → Tác động → Cách phát hiện → Các bước xử lý →
Leo thang. Khớp IR playbook 6 bước (Detect → Triage → Contain → Eradicate →
Recover → Post-mortem) học ở live T4.

## §17. AWS Cost Anomaly Detection

Dịch vụ ML của AWS Cost Management: học pattern chi tiêu, cảnh báo khi tốn bất
thường (vd ai đó bật cụm GPU). Hai object:

- `aws_ce_anomaly_monitor` — theo dõi phạm vi nào (toàn account / theo service).
- `aws_ce_anomaly_subscription` — ngưỡng + nơi nhận cảnh báo (email/SNS).

Bổ sung cho guardrail trong cluster (quota chặn *trong* cluster; cost anomaly bắt
chi phí *AWS-level* mà quota không thấy, vd NAT gateway, data transfer).

---

## Tài liệu nguồn (D1)

- Kubernetes RBAC — https://kubernetes.io/docs/reference/access-authn-authz/rbac
- OPA / Rego — https://www.openpolicyagent.org/docs
- Gatekeeper — https://open-policy-agent.github.io/gatekeeper
- ValidatingAdmissionPolicy — https://kubernetes.io/docs/reference/access-authn-authz/validating-admission-policy
- Kyverno — https://kyverno.io/docs
- EKS Best Practices (RBAC/IRSA) — https://aws.github.io/aws-eks-best-practices/security/docs

## Tài liệu nguồn (D2)

- AWS Secrets Manager — https://docs.aws.amazon.com/secretsmanager
- External Secrets Operator — https://external-secrets.io/latest
- Trivy — https://aquasecurity.github.io/trivy
- Cosign / Sigstore — https://docs.sigstore.dev/cosign/overview
- Kyverno verifyImages — https://kyverno.io/policies/?policytypes=verifyImages
- SLSA — https://slsa.dev/spec/v1.0/levels

## Tài liệu nguồn (D3)

- ResourceQuota — https://kubernetes.io/docs/concepts/policy/resource-quotas
- LimitRange — https://kubernetes.io/docs/concepts/policy/limit-range
- AWS Cost Anomaly Detection — https://docs.aws.amazon.com/cost-management/latest/userguide/manage-ad.html
- Chaos Mesh / Litmus — https://chaos-mesh.org · https://litmuschaos.io
- Google SRE Workbook (postmortem) — https://sre.google/workbook/example-postmortem
