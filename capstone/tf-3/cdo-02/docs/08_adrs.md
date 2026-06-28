# Architecture Decision Records - CDO-02 · Task Force 3

<!-- Doc owner: Nhóm CDO-02
     Status: Ongoing log W11-W12. Append-only - không xóa ADR cũ, superseded thì đánh dấu.
     Target: ≥3 ADR Pack #1 (W11) · ≥5 ADR Pack #2 (W12). -->

> Mỗi ADR = 1 quyết định có trade-off thật / reversal cost cao / sẽ bị panel probe.
> Format: Status · Date · Context · Decision · Consequence · Alternatives considered.

---

## ADR-001 - K8s-heavy / in-cluster Kubernetes Workflow Orchestration

- **Status**: Accepted
- **Date**: 2026-06-23
- **Context**: TF3 là self-heal cho 200+ microservice trên K8s/EKS. Action (restart/scale/adjust-memory/rollback) đều thao tác trực tiếp K8s workload. Cần chọn cách điều phối + thực thi vòng remediation phía CDO.
- **Decision**: Executor chạy **trong cluster** (Deployment ns `platform`, Python orchestration loop), điều phối detect→decide→5 guardrail→execute→verify→escalate, thực thi action qua **in-cluster ServiceAccount RBAC**. Đường nâng cấp: wrap **Argo Workflows** (visual DAG) ở W12 nếu kịp.
- **Consequence**:
  - ✅ Sát đề K8s self-heal, story Kubernetes-native mạnh khi pitch.
  - ✅ Thực thi bằng in-cluster SA scope namespace → **không cần kubeconfig ngoài**, dễ chứng minh least-privilege + zero unsafe action.
  - ✅ Latency thấp tới K8s API, reconcile drift tự nhiên.
  - ⚠️ Executor always-on pod (cost > serverless idle) — chấp nhận, 1 pod nhỏ.
  - ⚠️ Phải tự build orchestration + audit (không có execution history managed) → bù bằng audit chủ động mỗi bước.
- **Alternatives considered**:
  - Serverless (Step Functions + Lambda): scale-to-zero + audit managed, nhưng cần kubeconfig ngoài gọi EKS + xa workload → rejected.
  - Custom Go Operator (CRD): K8s-native nhất nhưng tốn thời gian build controller → để dành.

---

## ADR-002 - Namespace-per-tenant isolation (silo ở tầng namespace)

- **Status**: Accepted
- **Date**: 2026-06-23
- **Context**: Brief yêu cầu multi-tenant ≥2 tenant với RBAC isolation; Client xác nhận 2 tenant = 2 namespace. Leak cross-tenant = SEV1.
- **Decision**: Mỗi customer tenant = 1 namespace (`onlineboutique-tnt-a`, `onlineboutique-tnt-b`) + ServiceAccount + RBAC Role + NetworkPolicy deny-all + S3 audit prefix riêng. Executor đụng tenant nào dùng SA scope đúng namespace đó.
- **Consequence**:
  - ✅ Isolation strength cao, demo RBAC rõ (SA A không chạm namespace B).
  - ✅ Defense-in-depth blast-radius: RBAC namespace chặn đụng nhầm tenant.
  - ✅ Shared cluster → cost thấp hơn cluster-per-tenant.
  - ⚠️ Không cô lập tầng node/kernel (shared node) — chấp nhận cho sandbox.
- **Alternatives considered**:
  - Pool (shared ns + label filter): rẻ nhưng isolation yếu, khó demo deny → rejected.
  - Cluster-per-tenant: isolation tối đa nhưng quá nặng → rejected.

---

## ADR-003 - Istio + Prometheus làm nguồn telemetry / tracing / topology

- **Status**: Accepted
- **Date**: 2026-06-23
- **Context**: Engine train/test trên RE2/RE3 (Online Boutique + Istio); telemetry contract cần 5 signal generic (`service_error_rate`, `service_latency_p95`, `container_resource_usage`, `application_log_event`, `distributed_trace_error_event`) đúng schema. AI yêu cầu thêm Tracing + Topology graph (contract review P7).
- **Decision**: Deploy **Istio service mesh**; lấy metric từ Istio/Prometheus, trace từ Istio→OTel, topology từ **Kiali**. Shipper normalize về đúng schema contract (tên signal generic). Metric là suggest nhưng **schema + signal_name cố định** theo engine.
- **Consequence**:
  - ✅ Telemetry live khớp schema engine học từ CSV → detect không lệch.
  - ✅ Istio cấp metric + tracing + topology trong 1 stack (đáp ứng P7).
  - ✅ Bonus: Istio mTLS trong mesh.
  - ⚠️ Istio thêm sidecar overhead + thời gian cài (Helm) → plan sớm W12.
- **Alternatives considered**:
  - App-level custom metrics: lệch schema + không topology → rejected.
  - kube-state-metrics + cAdvisor thuần: thiếu request-level error/latency + trace/topology → rejected.

---

## ADR-004 - S3 Object Lock (Compliance mode, 90d) cho audit tamper-evident

- **Status**: Accepted
- **Date**: 2026-06-24
- **Context**: Brief + Client yêu cầu audit tamper-evident ≥90 ngày cho SOC2; brief loại hash-chain crypto.
- **Decision**: Ghi audit vào **S3 Object Lock Compliance mode** 90 ngày (WORM), CMK encryption; query qua **Athena**. Executor ghi 1 record mỗi bước remediation theo `correlation_id`.
- **Consequence**:
  - ✅ Compliance mode = không ai (kể cả root) xóa/sửa trong retention.
  - ✅ Athena query SQL cho mentor/auditor.
  - ✅ Đáp ứng SOC2 CC7.2 + CC8.1.
  - ⚠️ Compliance mode không rút ngắn retention được → config đúng ngay (test bucket riêng trước).
- **Alternatives considered**:
  - Append-only DynamoDB: query linh hoạt nhưng không WORM thật → rejected.
  - S3 Governance mode: bypass được bằng quyền đặc biệt → yếu hơn → rejected.

---

## ADR-005 - Live mode primary, RE2/RE3 CSV replay làm fallback

- **Status**: Accepted
- **Date**: 2026-06-24
- **Context**: AI engine thiết kế cho offline CSV (RE2/RE3). Brief + Client yêu cầu sandbox EKS thật, RBAC isolation thật, execution thật. AIO đã chốt 2 mode: "test = CSV+mock, **live = telemetry từ hệ thống CDO**". Engine API source-agnostic.
- **Decision**: CDO-02 chạy **Live mode làm chính**: telemetry từ cluster thật, execute action thật với 5 guardrail + audit thật. **CSV replay + mock** giữ làm fallback/dev nhanh.
- **Consequence**:
  - ✅ Giữ differentiation cốt lõi (RBAC/blast-radius/rollback/audit thật) — ăn điểm vs CDO-01 + đúng brief.
  - ✅ Không bắt AI đổi engine (API source-agnostic).
  - ⚠️ Live tốn công hơn (cluster, inject fault, Istio); fallback CSV giảm rủi ro demo.
- **Alternatives considered**:
  - Offline + mock primary: ít công nhưng mất differentiation + trái brief ("implemented + tested trên sandbox cluster") → rejected.

---

## ADR-006 - cert-expiring & queue-backlog là design-only pattern

- **Status**: Accepted
- **Date**: 2026-06-24
- **Context**: Brief: ≥3 implement + ≥2 design. Client nói cert-expiring tốn time on-call nhất. Nhưng 5 signal không cover cert expiry / queue depth, dataset RE2/RE3 không chứa 2 fault này (contract review P1).
- **Decision**: **Implement (3)**: OOMKilled (resource usage), service-stuck (latency/error_rate), code-fault (log/trace). **Design-only (2)**: cert-expiring, queue-backlog (paper playbook + diagram).
- **Consequence**:
  - ✅ 3 pattern implement bám đúng signal + dataset → khả thi + auto-resolve cao.
  - ✅ Thoả ≥3 implement + ≥2 design.
  - ⚠️ Pattern Client quan tâm nhất (cert) chỉ design-only → defend: telemetry contract chưa cover, roadmap thêm `cert_expiry_days`.
- **Alternatives considered**:
  - Implement cả cert/queue: cần thêm signal + action + dataset → vượt scope thời gian, sửa contract trước freeze → rejected.

---

## ADR-007 - AI decide-only, CDO executor execute (AI KHÔNG giữ kubeconfig)

- **Status**: Accepted (chốt với AIO T4 W11)
- **Date**: 2026-06-24
- **Context**: Deployment Contract bản draft cho AI Task Role quyền fetch `kubeconfig` + gọi EKS API để execute self-heal (§4.D, §6.B, §3 `self-heal-engine-sa`). Điều này mâu thuẫn boundary an toàn: nếu AI tự mutate K8s, CDO không enforce được safety gate / RBAC / audit nhất quán.
- **Decision**: Chốt boundary với AIO: **AI chỉ trả `action_plan` (decide), KHÔNG giữ kubeconfig, KHÔNG gọi EKS**. **CDO executor (in-cluster)** mới thực thi qua ServiceAccount RBAC scope namespace. Deployment Contract phải **bỏ quyền AI fetch kubeconfig + egress EKS API** trước freeze.
- **Consequence**:
  - ✅ Single execution boundary = CDO → enforce 5 guardrail + RBAC + audit nhất quán.
  - ✅ Giảm attack surface (AI không cầm cluster credential).
  - ✅ Khớp angle K8s-heavy (executor in-cluster SA, no external kubeconfig).
  - ⚠️ Cần AIO sửa contract; nếu AIO giữ kubeconfig thì phải re-negotiate (đã đồng ý bỏ T4).
- **Alternatives considered**:
  - AI execute trực tiếp K8s: nhanh cho AI demo nhưng vỡ safety/audit boundary + rủi ro quyền → rejected.
  - Shared execution AI+CDO: mơ hồ ownership → rejected.

---

## ADR-008 - CDO-02 tự host AI engine trong EKS + Bedrock qua IRSA

- **Status**: Accepted (chốt 25/06 W11)
- **Date**: 2026-06-25
- **Context**: Mentor announcement chốt mô hình *"mỗi CDO tự deploy engine lên platform riêng — AI không host hộ"*; rubric W12 chấm "engine deployed trên platform CDO" + differentiation. AIO giao engine dưới dạng **Docker image (artifact)**; engine dùng **AWS Bedrock Claude 3 Haiku** để suggest action (rule-based chỉ fallback, engine spec §2). (Endpoint chung `ai-engine.tf-3.internal` chỉ là skeleton bootstrap T5→đầu W12.)
- **Decision**: CDO-02 **tự host engine artifact** như **Deployment trong EKS** (ns `self-heal-system`, Service ClusterIP :8080, replicas min 2/max 10 + HPA CPU≥70% & Mem≥80%, resources 500m–1000m CPU / 1–2Gi · deployment-contract §2A/§2B), executor gọi qua **service DNS in-cluster** (`http://ai-engine.self-heal-system.svc.cluster.local:8080`). Engine pod dùng **IRSA** với quyền tối thiểu `bedrock:InvokeModel` (Claude 3 Haiku, us-east-1); chi phí Bedrock chịu trên **account CDO-2** (capstone có **$200 AWS credit**), giữ cost cap **$50/ngày/tenant** + fallback rule-based.
- **Consequence**:
  - ✅ Thoả rubric "engine trên platform CDO" + **giữ trọn differentiation K8s-heavy** (cả engine lẫn executor đều in-cluster).
  - ✅ Gọi nội bộ cluster → latency thấp, không cần ALB internal/PrivateLink xuyên VPC.
  - ✅ Boundary ADR-007 **không đổi**: engine vẫn decide-only (chỉ mở `/v1/*`), executor mới chạm K8s. Host ≠ cấp quyền cluster.
  - ⚠️ CDO-2 phải bật **Bedrock model access** (Claude 3 Haiku) trong account/region + provision IRSA Bedrock + chịu cost (đã có $200 credit, cost cap $50/ngày).
  - ⚠️ Engine là hộp đen (image AIO) — phụ thuộc AIO giao image đúng hạn (đầu W12); dùng skeleton chung để integrate sớm trước khi có image thật.
- **Alternatives considered**:
  - AIO host chung 1 endpoint ECS (như deployment-contract draft): mất differentiation, không thoả rubric → rejected (đẩy về đúng model mentor).
  - CDO host nhưng engine rule-based thuần (không Bedrock): nhẹ hơn nhưng AIO xác nhận dùng Bedrock thật → không chọn được.

---

## ADR-009 - Urgent direct-patch vs ArgoCD selfHeal: chống revert bằng `ignoreDifferences` (declarative)

- **Status**: Accepted (verified bằng thực nghiệm 26/06)
- **Date**: 2026-06-26
- **Context**: Tenant workload được ArgoCD quản (auto-sync + `selfHeal: true`). Path **urgent** (pattern_type=urgent) cho executor patch trực tiếp K8s API (SCALE_REPLICAS, PATCH_MEMORY_LIMIT) để phục hồi nhanh (RTO<60s). Nhưng ArgoCD selfHeal coi mọi thay đổi out-of-band là drift và **revert về desired-state trong Git** → lệnh urgent bị nuốt.
- **Evidence (thực nghiệm minikube + ArgoCD)**: deploy `guestbook` qua ArgoCD (`selfHeal=true`, Git desired `replicas=1`); executor mô phỏng urgent `kubectl scale --replicas=3`. Kết quả: app chuyển **OutOfSync** ngay, sau đó ArgoCD **tự revert `replicas` về 1** (xác nhận race condition; trên cluster đói CPU mất ~vài phút, EKS thật <15s).
- **Decision**: Khai báo **`spec.ignoreDifferences`** trong ArgoCD Application cho **các field do self-heal controller sở hữu** — `/spec/replicas` (SCALE_REPLICAS) và container `resources` (PATCH_MEMORY_LIMIT). ArgoCD bỏ qua các field này khi so drift → KHÔNG revert lệnh urgent; vẫn quản phần còn lại của manifest. Nguyên tắc: *"replicas/resources thuộc quyền self-heal controller (AI-driven), GitOps quản phần khai báo còn lại."* Các thay đổi **cấu hình vĩnh viễn** (ROLLOUT_UNDO, đổi config bền) đi **path deferred (Git commit/PR)** để không lệch Git.
- **Consequence**:
  - ✅ Urgent patch "dính" ngay, không bị revert — **không cần runtime sync-suspension** (không coupling ArgoCD API, không cần Git creds trong executor, không có window patch↔re-enable).
  - ✅ Executor giữ nguyên đơn giản (chỉ patch K8s) → ít lỗi, dễ test.
  - ⚠️ ArgoCD "mù" drift trên đúng 2 field đó — chấp nhận được vì đó là field self-heal chủ động đổi; vẫn audit mọi thay đổi qua executor.
  - ⚠️ ROLLOUT_UNDO không dùng urgent-patch trên ArgoCD-managed app (sẽ bị re-apply bản lỗi từ Git) → bắt buộc đi deferred.
- **Alternatives considered**:
  - **Runtime Sync-Suspension** (tắt auto-sync → patch → git push → bật lại, kiểu CDO-01): chứng minh được nhưng phức tạp (ArgoCD API + Git creds trong controller, có window race, nhiều bước dễ lỗi) → rejected, chọn declarative gọn hơn.
  - Tắt hẳn `selfHeal` cho tenant app: mất khả năng tự sửa drift do người ngoài đổi → rejected.
  - Urgent ghi thẳng Git rồi chờ sync: chậm (mất lợi thế fast-lane) → rejected.

---

<!-- Append ADR mới ở dưới. Superseded thì đánh dấu Status + link forward.
W12 có thể phát sinh: CI/CD tool, Argo Workflows adoption, GitOps sync strategy. -->
