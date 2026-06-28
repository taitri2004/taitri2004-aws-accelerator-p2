# Deployment & CI/CD Design - Task Force 3 · CDO-02

<!-- Doc owner: Nhóm CDO-02
     Status: Draft (W11 T4) → Final (W11 T6 Pack #1) → Working (W12 T4 Pack #2)
     Word target: 1200-2000 từ -->

> Hiện thực hạ tầng trong [`02_infra_design.md`](02_infra_design.md) (K8s-heavy, EKS 1.31 + Istio, executor in-cluster) theo IaC + CI/CD + GitOps + canary.

## 1. IaC strategy

### 1.1 Tool choice

- **IaC tool**: **Terraform** — hệ sinh thái AWS/EKS chín, module tái dùng, plan-on-PR rõ ràng. (CDK xét nhưng team quen Terraform hơn → giảm rủi ro thời gian W12.)
- **State backend**: S3 remote state (`tf-3-cdo2-tfstate`) + **S3 native lockfile** (`use_lockfile = true`, Terraform ≥1.10) — bỏ DynamoDB lock table, ít moving parts hơn. (DynamoDB chỉ còn dùng cho idempotency runtime, không dùng lock state.)
- **App/manifest**: Helm cho Online Boutique + Istio; ArgoCD sync K8s.

### 1.2 Module structure

```
infra/
├── modules/
│   ├── networking/        # VPC, subnet, SG, VPC endpoints, NAT          [built]
│   ├── eks/               # EKS 1.31 + node group + IRSA + secrets enc    [built]
│   ├── state-audit/       # DynamoDB idempotency + S3 Object Lock + Athena[built]
│   └── tenant-provision/  # namespace + RBAC + NetworkPolicy per tenant   [built]
├── environments/
│   └── sandbox/           # capstone POC                                  [built]
└── README.md

manifests/                 # K8s (ArgoCD sync) — W12                          [scaffolded]
├── platform/              # ai-engine ns self-heal-system (self-host + IRSA Bedrock + HPA, ADR-008) + NetworkPolicy (§5) + executor Deployment
├── istio/                 # Istio + Kiali
├── telemetry/             # OTel Collector + shipper
└── workload/              # Online Boutique per tenant
```

### 1.3 State management

- Remote state trên S3 cho `sandbox`; lock qua **S3 lockfile** (không cần DynamoDB lock).
- **Plan-on-PR** (comment kết quả) + **apply-on-merge** gate (manual approve cho sandbox cũng được do team nhỏ).

## 2. CI/CD pipeline

### 2.1 Pipeline stages (GitHub Actions)

```
PR ─► Lint/Validate ─► Test ─► Scan ─► tf plan ─► Review ─► Merge ─► tf apply ─► Smoke
```

| Stage | Tool | Việc | Quality gate |
|---|---|---|---|
| Lint/Validate | `tflint`, `tfsec`, `kubeval` | validate HCL + manifest | no error |
| Test | `pytest` (executor) | unit + integration (mock engine) | coverage ≥ 60% |
| Scan | **Trivy** + **gitleaks** | image CVE + secret leak | no CRITICAL, no secret |
| Plan | `terraform plan` | preview infra change | plan review |
| Apply | `terraform apply` | deploy infra | apply success |
| Smoke | custom script | bắn synthetic alert → chạy pipeline → check audit ghi | endpoints 200 + audit record |

### 2.2 Branch strategy

- `main` = deployable. `feature/*` → PR → review → merge.
- PR bắt buộc: pass scan + plan review trước merge `main`.
- **OIDC + IAM assume-role** cho GitHub Actions (no static AWS key trong CI).

### 2.3 Smoke test sau deploy

Self-Heal Engine deploy xong phải sẵn sàng cho detect→decide→verify, nên smoke test là gate bắt buộc. Kiểm tra tối thiểu:

- [ ] EKS cluster + 3 namespace `platform`, `onlineboutique-tnt-a`, `onlineboutique-tnt-b` tồn tại.
- [ ] **RBAC deny cross-tenant**: SA của tnt-a không patch được workload tnt-b (expect 403).
- [ ] Prometheus + AlertManager + Grafana + Kiali Ready.
- [ ] Executor pod + webhook receiver trả `/health` 200.
- [ ] Audit path hoạt động: bắn 1 synthetic alert → executor chạy hết vòng → **record query được bằng Athena** đúng prefix tenant.
- [ ] Nếu AI endpoint sẵn: verify đường gọi service nội bộ (`ai-engine.self-heal-system.svc`) + NetworkPolicy (Local Trust, không SigV4).

## 3. GitOps

- **ArgoCD** sync app/manifest (Online Boutique, Istio, executor config) từ Git.
- **Repo tách**: `infra` (Terraform) + `gitops` (manifest/Helm values).
- **Sync waves**:

| Wave | Components |
|---|---|
| 0 | namespace + RBAC + NetworkPolicy + secrets (ESO) |
| 1 | Istio control plane + CRD |
| 2 | Online Boutique workload (Istio injection ON) |
| 3 | Telemetry shipper + OTel + Kiali |

- **Drift detection**: ArgoCD auto-sync, prune disabled; destructive change cần manual approve.
- **Urgent-patch vs selfHeal (ADR-009)**: app tenant bật `selfHeal` sẽ **revert** lệnh urgent direct-patch (đã verify thực nghiệm: scale 3→1). Khắc phục **khai báo** bằng `ignoreDifferences` cho field self-heal controller sở hữu (`/spec/replicas`, container `resources`) — xem [`../manifests/gitops/tenant-app.yaml`](../manifests/gitops/tenant-app.yaml). KHÔNG dùng runtime sync-suspension (tránh coupling + window race). ROLLOUT_UNDO/config bền đi path deferred.

## 4. Deployment strategy

### 4.1 Strategy — Canary / progressive (theo deployment contract §7)

- **Executor Deployment**: rolling update (hoặc Argo Rollouts canary 10→50→100% nếu kịp W12).
- **Abort criteria** (auto-rollback ngay khi vướng):
  - 5xx error rate > 1%
  - **p99 latency theo TỪNG endpoint** (deployment-contract §6.B — tránh rollback giả khi `/v1/decide` gọi LLM ~2500ms): `/v1/detect` > **800ms** · `/v1/decide` > **3000ms** (khớp đúng SLA p99 ai-api §4) · `/v1/verify` > **1000ms**.
  - Health/readiness (liveness) fail liên tiếp quá ngưỡng.
- Áp cho cả engine rollout (do AI) và platform component (executor/telemetry).

### 4.2 Rollback method (tách 3 tầng)

**1. Rollback deployment platform** (đổi version executor/manifest):
- Primary: ArgoCD sync lại Git commit SHA ổn định trước.
- Secondary: `kubectl rollout undo` Deployment.
- Target RTO: < 60 giây.

**2. Rollback self-heal runtime action** (khi action sửa lỗi gây regression):
- Tương ứng `rollback_plan` đi kèm `action_plan` AI trả về (restore pre-state snapshot — scale/memory/rollout undo).
- Là bước riêng trong executor (xem [`02_infra_design.md`](02_infra_design.md) §3.1).
- Nếu rollback không an toàn/không đủ điều kiện → **escalate**, không mutate thêm.

**3. Rollback infrastructure** (Terraform):
- Không rollback tự động kiểu transaction. Cách an toàn: review → sửa code về trạng thái hợp lệ → `plan` lại → `apply`.

> Nguyên tắc fail-safe: khi không chắc → dừng / rollback / escalate, không tiếp tục deploy/mutate.

## 5. Environment separation

| Env | Purpose | Auto-deploy |
|---|---|---|
| Sandbox | Capstone POC (demo) | apply on merge `main` (+ manual gate) |
| Staging | Pre-prod (skeleton, post-capstone) | on merge `develop` |

## 6. Secrets in pipeline

- CI lấy AWS access qua **OIDC + assume-role** (no static key).
- **gitleaks/TruffleHog** scan PR, block merge nếu lộ.
- Secret runtime (webhook JWT, Slack) ở Secrets Manager, lấy qua IRSA/ESO — không bao giờ vào Git/image. **Không còn kubeconfig** (executor dùng in-cluster SA, ADR-007). Xem [`03_security_design.md`](03_security_design.md) §3.

## 7. Tenant onboarding deployment

```
1. Khai báo tenant (tenant_id, tier) → trigger module `tenant-provision`
2. Provision: namespace + NetworkPolicy deny-all + ServiceAccount + RBAC Role/RoleBinding
   + S3 audit prefix + allowlist entry + ResourceQuota/LimitRange
3. ArgoCD deploy Online Boutique vào namespace (Istio injection ON)
4. Smoke test: synthetic alert → pipeline chạy → verify audit ghi đúng prefix tenant
5. Mark tenant ready
```

Target: < 30 phút (validate W12).

## 8. Observability stack

| Layer | Tool |
|---|---|
| Metrics | Prometheus (Istio) + kube-state-metrics + node-exporter + CloudWatch |
| Logs | CloudWatch Logs (executor) + Logs Insights |
| Traces | OTel Collector → Jaeger / X-Ray |
| Topology | Kiali (service graph, cấp cho engine — P7) |
| Dashboards | Grafana / CloudWatch |
| Alerts | AlertManager (trigger self-heal) + CloudWatch Alarms (SLO) |
| Audit trail | S3 Object Lock + **Athena query** (ADR-004) |

## 9. Open questions

- [ ] Q1: Executor rollout — K8s rolling update đủ, hay làm Argo Rollouts canary cho demo đẹp hơn?
- [ ] Q2: ArgoCD self-host trên cluster hay dùng add-on managed? (cân nhắc cost + thời gian)

## Related documents

- [`02_infra_design.md`](02_infra_design.md) - kiến trúc deploy theo strategy này
- [`03_security_design.md`](03_security_design.md) - CI/CD security gate (gitleaks/Trivy/OIDC) + secrets
- [`05_cost_analysis.md`](05_cost_analysis.md) - cost của các component deploy ở đây
- [`08_adrs.md`](08_adrs.md) - ADR-003 (Istio), ADR-004 (audit)
