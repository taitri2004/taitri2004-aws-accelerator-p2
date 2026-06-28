# Requirements Analysis - Task Force 3 · CDO-02

<!-- Doc owner: Nhóm CDO-02
     Status: Draft (W11 T2-T3) → Final (W11 T6 Pack #1) → Refined (W12 T4 Pack #2)
     Word target: 800-1500 từ
     LƯU Ý: §4 "Comparison với 2 nhóm cùng task force" đã BỎ theo chỉ đạo mentor
     (các nhóm không được biết solution của nhau). -->

## 1. Đề tài context

Task Force 3 build **Self-Heal Engine** — hệ thống auto-remediation cho Kubernetes: khi sự cố known-pattern xảy ra thì tự `detect → match runbook → execute (audited) → verify → escalate nếu fail`, để on-call engineer không bị đánh thức vì việc lặp lại (Client: VP Engineering, SaaS B2B, 200+ microservice EKS, ~120 tenant). Nhóm AI (AIO-04) build engine ra quyết định (3 endpoint `/v1/detect`, `/v1/decide`, `/v1/verify`, host trên ECS Fargate); **CDO-02 build platform hạ tầng + executor (in-cluster)** thực thi action an toàn + audit + multi-tenant isolation. AI chỉ đề xuất action plan, **không tự self-heal, không giữ kubeconfig** — toàn bộ execution + safety + audit là việc CDO (ADR-007).

## 2. Infra non-functional requirements

| NFR | Target | Justification |
|---|---|---|
| Auto-resolve rate | ≥ 60% trên ≥10 scenarios | Client hard requirement |
| Latency alert → action | < 60 giây | Client expect |
| Verify window | ổn định ~5p, configurable per pattern | Client: "resolved" = metric normal + giữ ổn định, không phải lệnh chạy xong |
| Platform availability | ≥ 99.5% | Subscription SLA |
| Zero unsafe action | 0 (no prod-ns delete, no IAM modify) | Client hard requirement |
| Audit retention | ≥ 90 ngày, tamper-evident | SOC2 Type II re-cert tháng 9 |
| Multi-tenant isolation | ≥ 2 tenant, RBAC, no cross-leak | Brief; leak = SEV1 cap tier |
| Tenant onboarding | < 30 phút | Sales requirement (production target) |
| Rollback RTO | < 60 giây | Brief safety checkpoint |
| Test window | ≥ 4 giờ scenario simulation | Brief (không cần 1-week real) |

## 3. Differentiation angle (KEY)

- **Angle chọn**: **K8s-heavy / in-cluster Kubernetes Workflow Orchestration** — executor chạy **trong cluster** (Deployment ns `platform`), điều phối nguyên vòng self-heal và thực thi action qua **in-cluster ServiceAccount RBAC** (không cần kubeconfig ngoài). 5 safety checkpoint là các bước tường minh trong orchestration loop. Chi tiết [`02_infra_design.md`](02_infra_design.md) §3, lý do [`08_adrs.md`](08_adrs.md) ADR-001.
- **Why this angle**:
  - *Sát đề K8s self-heal*: executor sống cạnh workload, thao tác K8s native → story Kubernetes-native mạnh khi pitch.
  - *Bảo mật/operational control*: thực thi bằng in-cluster SA scope namespace, **không cần kubeconfig ngoài** → least-privilege + zero unsafe action dễ chứng minh; latency thấp tới K8s API.
  - *Đường nâng cấp*: orchestration loop wrap được bằng **Argo Workflows** (visual DAG) ở W12 nếu kịp.
- **Trade-off chấp nhận**: executor always-on pod (cost > serverless idle) — chấp nhận, 1 pod nhỏ; phải tự build orchestration + audit (bù bằng audit chủ động mỗi bước).
- **Locked**: T3 W11 (fastest-commit wins) — commit angle sớm, tránh trùng nhóm CDO còn lại.

## 4. (Đã bỏ — Comparison với 2 nhóm cùng task force)

> Mentor chỉ đạo bỏ mục so sánh trực tiếp giữa các nhóm CDO vì các nhóm không được biết solution của nhau. So sánh với **approach kiến trúc generic** (operator / raw Lambda) đặt ở [`02_infra_design.md`](02_infra_design.md) §3.2 + [`08_adrs.md`](08_adrs.md).

## 5. Constraints

- **Live mode primary**: telemetry + execution thật trên sandbox EKS; RE2/RE3 CSV replay làm fallback (ADR-005).
- **Schema cố định**: metric là suggest nhưng payload + API call phải đúng schema AI yêu cầu; bộ `signal_name` engine cần là cố định.
- **EKS 1.31** (khớp Client n-1 policy), us-east-1, multi-AZ.
- **AWS only**, no multi-cloud. **Sandbox + synthetic workload only** (no production traffic).
- **3 contracts FREEZE T5 W11** — interface AI-CDO không đổi ngoài change request.
- **Code freeze 8h T5 02/07 W12**.
- Auth AI endpoint: **Local Trust in-cluster + K8s NetworkPolicy** (contract 25/06, không SigV4 cho call in-cluster); IRSA cho AWS services; alert→receiver JWT bearer. Istio mTLS trong mesh là bonus.

## 6. Open questions

- [ ] Q1: Bộ `signal_name` engine bắt buộc có (contract review Q7) — *resolve với AIO trước T5*.
- [ ] Q2: Topology graph format + tracing (contract review P7/Q8) — *resolve với AIO trước FREEZE*.
- [ ] Q3: `tenant_id` payload = customer (tnt-a) hay CDO (cdo-2)? (P2) — *resolve với AIO*.
- [ ] Q4: Verify window 5p config ở đâu (executor Wait step hay engine)? (P4) — *resolve với AIO*.
- [x] Q5 (RESOLVED): AI có giữ kubeconfig không → **Không**. AI decide-only, CDO executor execute qua in-cluster SA (ADR-007). Deployment contract bỏ quyền AI fetch kubeconfig/EKS trước freeze.

## Related documents

- [`02_infra_design.md`](02_infra_design.md) - kiến trúc hiện thực các NFR này
- [`03_security_design.md`](03_security_design.md) - security baseline đáp ứng NFR isolation + audit
- [`08_adrs.md`](08_adrs.md) - quyết định kiến trúc + lý do
- [`../contract-review-notes.md`](../contract-review-notes.md) - accept/push-back 3 contracts
