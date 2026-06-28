# Contract Review Notes — TF3 Self-Heal Engine · CDO-02

> Review 3 contracts AI publish (telemetry · ai-api · deployment) trước khi ký T5 W11.
> Mục tiêu: ghi rõ phần ACCEPT + phần PUSH-BACK (có lý do) → gửi AIO-04 tối T4, co-design T5 sáng, ký T5 chiều.
> Đây là evidence cho pillar **Contract Acceptance (20% điểm W11)**.

- **Reviewer**: <tên> (CDO-02)
- **Ngày review**: 2026-06-24 (T4 W11) · contract version `v1.0`
- **Trạng thái**: 🟡 Conditional accept — ký được sau khi giải quyết blocker §0 + push-back §2

---

## 0. ✅ RESOLVED — 2 mode: Test (CSV+mock) vs Live (telemetry từ CDO)

**Chốt với AIO (T4 W11)**: tách rõ 2 mode, cùng dùng chung API engine:
- **Test/Eval mode**: AIO replay CSV RE2/RE3 + mock execution → để AI train/eval model detection (precision/recall). Cũng là **fallback** của CDO khi cluster chưa sẵn.
- **Live mode**: telemetry lấy từ **hệ thống thật của CDO** (sandbox EKS 1.31 + Online Boutique), CDO **execute action thật** với 5 safety guardrail + audit thật. → Phần demo ăn điểm vs CDO-01.

Làm được mà không bắt AIO đổi engine vì engine không quan tâm nguồn telemetry hay action thật/mock: `/v1/detect` nhận `telemetry_window` (CDO gửi từ CSV hay live đều cùng schema), `/v1/decide` chỉ trả plan (CDO chọn execute), `/v1/verify` nhận post-telemetry (CDO gửi).

**⚠️ Hệ quả #1 — signal schema phải khớp 2 mode**: engine train/test trên signal của RE2/RE3 (Online Boutique + Istio). Nên telemetry **live của CDO bắt buộc emit ĐÚNG 5 signal cùng schema** (`istio_request_error_rate`, `istio_request_latency_p95`, `container_memory_working_set_bytes`, `app_log_error_event`, `trace_span_error_event`). → CDO-02 deploy **Online Boutique + Istio** trên sandbox để telemetry live khớp CSV. (Điều chỉnh P5: **GIỮ Istio** cho nhất quán, không bỏ.)

**⚠️ Hệ quả #2 — pattern bị giới hạn bởi dataset**: pattern implement-được-live = pattern engine biết từ RE2/RE3 (OOM, service-stuck, code-fault). Cert-expiring / queue backlog không có trong dataset + không có signal → **design-only** (xem P1).

Chỉ cần sửa contract nhẹ: deployment §2.D cho phép live execution (không chỉ mock); §3 RBAC thêm per-tenant-namespace (P3).

---

## 0b. Clarifications mới từ AIO (T4 W11)

1. **Metric là "suggest", schema là BẮT BUỘC**: 5 metric trong telemetry contract chỉ gợi ý — CDO được dùng metric/nguồn khác, NHƯNG payload phải đúng **schema AI yêu cầu** + request/response API đúng schema. → Engine detect key theo `signal_name` + ý nghĩa, nên bộ signal_name vẫn cố định dù metric linh hoạt (xem Q7).
2. **AI chỉ trả action plan, KHÔNG tự self-heal**: execution + 5 safety guardrail + audit = 100% việc CDO → củng cố differentiation CDO-02.
3. **AI yêu cầu CDO cấp thêm Tracing + Topology graph** (service dependency graph) — localize lỗi cross-service + reasoning blast-radius. ⚠️ **Yêu cầu MỚI chưa có trong telemetry contract** → phải định nghĩa schema + thêm vào trước FREEZE (xem P7).
4. **Mai AI giao mock API version** → CDO integrate executor + test code path (detect/decide/verify + 400/409/429/503 + fallback) ngay, không chờ engine thật.

**Tác động Istio**: cần thêm Tracing + Topology, mà Istio cho cả metric + distributed tracing + topology (Kiali) trong 1 stack → cài Istio càng hợp lý.

---

## 0c. UPDATE 24/6 — Contract chính thức FREEZE (AIO publish trên `main`) đã giải quyết phần lớn push-back

AIO publish 3 contract chính thức (JSON Schema draft-07) tại `tf-3/ai/contracts/` + tự review (`dataset/contracts/REVIEW-...md`). Đối chiếu với push-back §2 + open questions §3:

| Mục | Trạng thái sau FREEZE |
|---|---|
| **§0 blocker (kubeconfig/ADR-007)** | ✅ RESOLVED — deployment §3.A.2/§3.D cấm `eks:*`+kubeconfig, §5.B egress không mở EKS API. "AI=Brain, CDO=Hands". (AIO tự nêu là CRITICAL C1, chọn đúng phương án CDO-executes.) |
| **P1 / P6** (cert/queue signal + action) | ✅ Chốt **design-only** — telemetry vẫn 5 signal, không thêm `cert_expiry/queue_depth`. Action enum mới: `RESTART_DEPLOYMENT, PATCH_MEMORY_LIMIT, SCALE_REPLICAS, ROLLOUT_UNDO, ROTATE_SECRET, DELETE_POD` (đổi tên so với draft). |
| **P2 / Q3** (tenant 2 tầng) | ✅ RESOLVED — `X-Tenant-Id` routing = **cdo-2 UUID `6c8b4b2b-4d45-4209-a1b4-4b532d56a31c`** (deployment §2.C); telemetry datapoint `tenant_id` = per-customer UUID (field riêng). |
| **P4 / Q4** (resolved + verify window) | ✅ RESOLVED — `/v1/decide` trả `verify_policy.window_seconds` + `success_conditions`; executor dùng giá trị engine (fallback CFG). |
| **P5 / Q5 / Q7** (signal mandatory + Istio) | ✅ RESOLVED — 5 `signal_name` generic là enum bắt buộc (`service_error_rate, service_latency_p95, container_resource_usage, application_log_event, distributed_trace_error_event`); metric/nguồn linh hoạt → Istio là lựa chọn của CDO, không bị contract ép tên `istio_*`. |
| **Q2** (dataset scenario) | ✅ RESOLVED — dataset RE2 (resource/network cpu/mem/disk/socket/delay/loss) + RE3 (code f1-f5); không có cert/queue → khớp design-only. |
| **Q6** (latency) | ✅ RESOLVED — SLA: detect <300ms, **decide <3000ms** (nới cho Bedrock LLM), verify <500ms → alert→action <60s vẫn khả thi. |
| **Q9** (mock API) | ✅ RESOLVED — demo API branch `feat/demo`; executor đã test khớp (3/3 + E2E RESOLVED). |
| **P3** (RBAC per-namespace) | 🟡 PARTIAL — deployment §1.5 để namespace cấu hình động, CDO tự validate `[namespace, deployment]`; thiết kế 2 namespace per-tenant của mình hợp lệ. |
| **P7 / Q8** (topology graph) | 🟡 PARTIAL — telemetry labels đã có `trace_id/span_id/operation` (tracing OK), nhưng **schema topology graph vẫn CHƯA có trong contract** → CDO cấp qua Kiali (chưa chốt format với AIO). |

**Nghĩa vụ MỚI từ telemetry §2.5 (chưa có trong review cũ):** CDO phải (a) **scrub PII/secret** trong stack trace `application_log_event` ở ingestion; (b) **DLQ** cho malformed + alert >0.5%/5min. → đã thêm vào `docs/03_security_design.md §5.3`.

**Lệch demo vs contract (nhẹ):** contract nói schema sai = `400`, demo trả `422` (executor map cả hai); contract bắt detect response có `reasoning`, demo chưa trả.

---

## 1. ACCEPT — nhận build theo contract (spec rõ ràng, hợp lý)

Các điều khoản dưới đây CDO-02 chấp nhận, không cần đổi:

**Deployment Contract:**
- ✅ AI Engine shared trên ECS Fargate, 2 CDO point chung endpoint `ai-engine.tf-3.internal` qua `tenant_id` (§2.C).
- ✅ Internal ALB, private subnet multi-AZ, no public IP, Route 53 private zone (§6).
- ✅ Security Group `tf-3-ai-engine-sg`: chỉ CDO-1/CDO-2 SG → port 8080, default-deny; egress chỉ tới Secrets Manager/Bedrock/DynamoDB/S3/EKS API qua VPC endpoint (§6.B).
- ✅ Idempotency lock: DynamoDB conditional write (`tf-3-aiops-idempotency-lock`) hoặc Redis TTL 5p, trùng key → `409` (§5.A).
- ✅ Audit S3 Object Lock **Compliance mode 90d** (`tf-3-aiops-audit-trail`) + CDO cấp Athena/UI query (§5.B).
- ✅ RBAC Role + RoleBinding apply trên sandbox cho **CDO executor in-cluster SA** (§3). ⚠️ **Sửa**: AI KHÔNG giữ kubeconfig nữa (ADR-007) — bỏ `tf-3/ai-engine/kubeconfig` secret + egress EKS API của engine khỏi deployment contract trước freeze.
- ✅ Canary 10→50→100%; abort khi 5xx>1% / p99>800ms; rollback RTO <60s ArgoCD→ECS (§7).
- ✅ Health/Ready/Metrics endpoint trên 8080; ALB health check 30s/2-healthy/3-unhealthy (§8).
- ✅ Failure modes: task crash auto-restart, Bedrock 429 → backoff + fallback rule-based, mất DynamoDB/S3 → fallback static runbook (§9.B).
- ✅ IAM tách Execution Role / Task Role least-privilege, cấm `iam:*`/`ec2:*` (§4).

**AI API Contract:**
- ✅ 3 endpoint `detect` → `decide` → `verify`, luồng + schema rõ (§3).
- ✅ `decide` trả `blast_radius_config` (`max_pod_impact_pct`, `circuit_breaker_error_rate`, `allowed_namespaces`) — CDO dùng để enforce (§3 EP2).
- ✅ `verify` trả `next_action` (DONE/RETRY/ROLLBACK/ESCALATE) + `escalation_bundle` (§3 EP3).
- ✅ Error codes 400/409/429/503; **CDO bắt buộc fallback khi 503** (static runbook / escalate) (§4).
- ✅ Rate limit 120 req/min/tenant.

**Telemetry Contract:**
- ✅ CDO chịu trách nhiệm thu thập + chuẩn hóa + emit signal qua SQS, preprocess counter→gauge, inject `tenant_id`, anonymize PII (§2, §4).
- ✅ Timestamp RFC3339 UTC millisecond.

> **Ghi chú quan trọng cho doc Security/Infra**: contract chỉ **đưa config** blast-radius; **ENFORCE 5 safety checkpoint là việc của CDO** — engine gợi ý, CDO mới là bên chặn. RBAC scope đúng `allowed_namespaces` = enforce allowlist default-deny (defense-in-depth: engine bảo làm ngoài allowlist thì RBAC vẫn chặn).

---

## 2. PUSH-BACK — yêu cầu sửa/làm rõ trước khi FREEZE

| # | Vấn đề | Contract hiện tại | Vì sao cần đổi | Đề xuất sửa |
|---|---|---|---|---|
| P1 | **Thiếu signal cho cert-expiring & queue backlog** | Telemetry chỉ có 5 signal: error_rate, latency_p95, memory, log error, trace error | Client nói **cert-expiring tốn time nhất**; queue backlog top frequency. Không có signal → không detect được | Hoặc thêm signal (`cert_expiry_days`, `queue_depth`), hoặc thống nhất xếp 2 pattern này vào **design-only** (≥2 designed), implement OOM + service-stuck + code-fault |
| P2 | **Tenant model lẫn 2 tầng** | Deployment routing dùng `X-Tenant-Id = cdo-2`; Telemetry payload dùng `tnt-re2-simulation` | Lẫn giữa (a) tenant = CDO nào (routing engine) và (b) 2 customer tenant trong cluster (brief yêu cầu isolation) | Chốt nhất quán across 3 contract: header `X-Tenant-Id = cdo-2` cho routing; payload thêm field customer tenant (vd `tnt-a`/`tnt-b`) để demo isolation |
| P3 | **RBAC chỉ 1 namespace** | Role/RoleBinding chỉ cho `onlineboutique` (deployment §3); `allowed_namespaces: ["onlineboutique"]` | Client: 2 tenant = 2 namespace để chứng minh RBAC isolation | Cần RBAC + ServiceAccount **per-tenant-namespace** (vd `onlineboutique-a`, `onlineboutique-b`), `allowed_namespaces` gồm cả 2 |
| P4 | **Định nghĩa "resolved" chưa khớp** | `verify` trả `success` từ `post_telemetry_window` (ví dụ chỉ 1 datapoint @10:02) | Client: "resolved" = metric về normal **+ ổn định 1 window ~5p, configurable per pattern** — không phải "lệnh chạy xong" | `verify` phải đánh giá trên window ổn định 5p (configurable per pattern); CDO gửi đủ window; AI confirm logic |
| P5 | **Istio bắt buộc cho live** (đã quyết — xem §0) | 3/5 signal là Istio (`istio_request_error_rate`, `istio_request_latency_p95`) | Live telemetry phải khớp schema engine train (RE2/RE3 + Istio) → BẮT BUỘC có Istio trên sandbox, không bỏ được | GIỮ Istio: deploy Online Boutique + Istio addon; plan cài Istio (Helm) sớm trong W12 |
| P6 | **Action set chưa cover cert/queue** | `decide` action enum: RESTART_DEPLOYMENT, SCALE_UP_PODS, UPDATE_ENV_SECRET, ADJUST_MEMORY_LIMIT | Không có action rotate-cert / scale-worker rõ ràng | Nếu cert/queue là design-only thì OK; nếu implement, thêm action `ROTATE_TLS_CERT`, `SCALE_WORKER` |
| P7 | **Tracing + Topology graph chưa có trong contract** (yêu cầu mới T4) | Telemetry contract chỉ có 5 signal, không có topology/service-graph | AI yêu cầu để localize lỗi cross-service + reasoning blast-radius; thêm sau FREEZE phải qua change request | Định nghĩa schema topology (nodes=service, edges=dependency; format JSON adjacency / OTel service map) + cơ chế tracing (OTel→collector / Istio→Jaeger); **thêm vào telemetry contract trước FREEZE** |

---

## 3. Open questions gửi AIO-04 / mentor (cần trả lời trước T5 — chú ý ~24h)

- [ ] Q1 (blocker §0): Engine `decide`/`verify` chạy được với **telemetry live** từ cluster CDO-2, hay chỉ CSV RE2/RE3? CDO-2 muốn demo live.
- [ ] Q2: RE2/RE3 dataset có chứa scenario OOMKilled / cert-expiring / queue backlog không, hay chỉ code/resource fault của Online Boutique (f1-f5)?
- [ ] Q3: `tenant_id` trong payload telemetry = id CDO (`cdo-2`) hay id customer (`tnt-a`)? (liên quan P2)
- [ ] Q4: Verify window ổn định 5p — engine support configurable per pattern chứ? (P4)
- [ ] Q5: Danh sách signal **bắt buộc** vs optional — để CDO biết có cần cài Istio không. (P5)
- [ ] Q6: Latency budget alert→action — Client expect <60s. Engine detect <300ms + decide <500ms; CDO execute trong budget còn lại. Confirm OK.
- [ ] Q7: Bộ `signal_name` engine **bắt buộc** có là gì? (metric linh hoạt nhưng detect key theo tên + ý nghĩa)
- [ ] Q8: Topology graph cần **format gì** (JSON adjacency / OTel service map / Kiali export), **static hay live-update**, gửi qua endpoint/signal nào? Tracing format (OTel spans)?
- [ ] Q9: Mock API mai — xin **URL + schema chính xác** + ví dụ response từng endpoint để build executor.

---

## 4. Trạng thái ký (cập nhật T5)

| Contract | Trạng thái | Điều kiện ký |
|---|---|---|
| Telemetry | 🟢 Accept | P1/P5 chốt design-only + 5 signal generic; còn bổ sung topology (P7) — non-blocking, làm qua change request |
| AI API | 🟢 Accept | P4/P6 đã resolved trong bản FREEZE (verify_policy + action enum mới) |
| Deployment | 🟢 Accept | blocker §0 (kubeconfig) resolved; P3 namespace để CDO cấu hình động |

> Cập nhật sau khi AIO publish contract chính thức trên `main` (24/6): phần lớn push-back đã được giải quyết (xem §0c). Còn lại P7 (format topology graph) là việc cần chốt format với AIO nhưng **không chặn ký** (thêm field optional = non-breaking change).

- **Kết quả co-design T5 sáng**: <điền sau>
- **Đã ký T5 chiều**: <điền sau khi mentor witness>

## Related documents

- [`understanding-personal.md`](understanding-personal.md) — cách hiểu đề + notes Client Q&A
- [`debrief-t2-w11.md`](debrief-t2-w11.md) — debrief gửi mentor
- `docs/02_infra_design.md` — kiến trúc hiện thực các điều khoản accepted
- `docs/03_security_design.md` — RBAC, blast-radius enforce, audit Object Lock
