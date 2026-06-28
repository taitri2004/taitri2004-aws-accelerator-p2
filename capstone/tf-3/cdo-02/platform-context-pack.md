# Platform Context Pack — CDO-02 → AIOps (TF3 Self-Heal)

> Trả lời `AIOPS_TO_CDOPS_CONTEXT_REQUEST`. Nguồn: [`docs/02_infra_design.md`](docs/02_infra_design.md), [`docs/03_security_design.md`](docs/03_security_design.md), [`contract-review-notes.md`](contract-review-notes.md), [`infra/`](infra/), [`executor/`](executor/).
> Mode: **Live** (EKS 1.31 + Online Boutique + Istio) primary, **CSV RE2/RE3 replay** fallback (ADR-005).

## 0. Tóm tắt quyết định CDO-02 (cần AIO xác nhận lại)

1. **Signal names**: CDO adopt 5 tên generic AIO mới đưa (`service_error_rate`,...). Map từ Istio/Prometheus → schema contract. (Bản telemetry-contract Istio cũ → coi như superseded bởi tên generic này; cần chốt 1 canonical trước freeze.)
2. **`tenant_id` = UUID per customer tenant**, dùng **cả ở header `X-Tenant-Id` lẫn payload** (nhất quán P2):
   - `tnt-a` → `a1a1a1a1-0000-4000-8000-000000000001`
   - `tnt-b` → `b2b2b2b2-0000-4000-8000-000000000002`
3. **CDO enrich được `labels.namespace` + `labels.deployment`** cho mọi action-able signal (✅ vì CDO own cluster + Istio) → AIO đưa vào `anomaly_context` + `action_plan` chính xác.
4. **Audit single-writer = CDO executor (in-cluster)** ghi mỗi bước theo `correlation_id` để tamper-evidence nhất quán; AIO không ghi trực tiếp, dữ liệu decision lấy từ response `/v1/decide`. (Nếu AIO muốn ghi trực tiếp, CDO expose audit-write endpoint — báo sớm.)
5. **Verify window 5 phút, configurable per pattern**; CDO query Prometheus build `post_telemetry_window`.
6. **AI decide-only, KHÔNG giữ kubeconfig / KHÔNG gọi EKS** (đã chốt T4): CDO executor (in-cluster SA) thực thi. Deployment contract cần bỏ quyền AI fetch kubeconfig + egress EKS API trước freeze (ADR-007).

---

## 1. Cluster Topology ⭐

EKS 1.31, us-east-1 multi-AZ. Workload = **Online Boutique (hipstershop)** deploy đầy đủ trong **mỗi** namespace tenant (chứng minh isolation). Istio injection ON.

| Tenant | Namespace | Service | Deployment | Depends on | Notes |
|---|---|---|---|---|---|
| tnt-a | onlineboutique-tnt-a | frontend | frontend | productcatalog, cart, checkout, currency, recommendation, shipping, ad | public-facing |
| tnt-a | onlineboutique-tnt-a | checkoutservice | checkoutservice | cart, payment, shipping, email, currency, productcatalog | critical |
| tnt-a | onlineboutique-tnt-a | cartservice | cartservice | redis-cart | stateful dep |
| tnt-a | onlineboutique-tnt-a | redis-cart | redis-cart | — | stateful, careful |
| tnt-b | onlineboutique-tnt-b | frontend | frontend | (như tnt-a) | isolated khỏi tnt-a (NetworkPolicy) |
| tnt-b | onlineboutique-tnt-b | checkoutservice | checkoutservice | ... | critical |

> Topology graph (P7): cấp realtime qua **Kiali** (Istio service graph) + export OTel service map. Format đề xuất: JSON adjacency `{node, edges[]}` — chốt format với AIO (Q8).

## 2. Service Catalog + Tenant Mapping ⭐

| Service | Namespace | Tenant | Deployment | Criticality | Allowed actions |
|---|---|---|---|---|---|
| frontend | onlineboutique-tnt-a | tnt-a | frontend | high | restart, rollback (dry-run + strict verify) |
| checkoutservice | onlineboutique-tnt-a | tnt-a | checkoutservice | high | restart, rollback |
| paymentservice | onlineboutique-tnt-a | tnt-a | paymentservice | high | restart, rollback |
| cartservice | onlineboutique-tnt-a | tnt-a | cartservice | medium | restart, scale |
| recommendationservice | onlineboutique-tnt-a | tnt-a | recommendationservice | low | restart, scale |
| emailservice | onlineboutique-tnt-a | tnt-a | emailservice | medium | restart, adjust_memory |
| redis-cart | onlineboutique-tnt-a | tnt-a | redis-cart | high | restart only / escalate (stateful) |

*(tnt-b mirror y hệt trong `onlineboutique-tnt-b`.)*

## 3. Allowed Action Matrix ⭐

| Action | Resource | Allowed? | Limit | Notes |
|---|---|---|---|---|
| RESTART_DEPLOYMENT | Deployment | yes | max 1 deployment/action, chỉ namespace tenant | rolling restart qua annotation |
| SCALE_UP_PODS | Deployment | yes | max +3 replica, max 5 total | worker/non-critical (trừ khi approve) |
| ADJUST_MEMORY_LIMIT | Deployment | yes | max +50% current limit | requires pre-state snapshot |
| ROLLBACK (rollout undo) | Deployment | yes | previous revision only | requires verify after |
| delete pod | Pod | limited | max 1 pod, non-critical | prefer restart deployment |
| delete namespace | Namespace | **never** | — | unsafe action |
| modify IAM | IAM | **never** | — | out of scope |

> Enforce 2 lớp: (1) executor blast-radius check (`max_pod_impact_pct`, `allowed_namespaces`); (2) **K8s RBAC scope namespace tenant** (in-cluster SA) — kể cả engine trả action ngoài allowlist, RBAC vẫn chặn → "zero unsafe action".

## 4. RBAC Contract ⭐

1 controller ServiceAccount `tf3-cdo-controller` (ns platform, §3.D), Role+RoleBinding tạo **per namespace tenant**, scope **chỉ namespace đó** (Terraform: [`infra/modules/tenant-provision`](infra/modules/tenant-provision/main.tf), khớp deployment contract §3.D):

| Resource | Verbs | Namespace scope | Used for |
|---|---|---|---|
| pods, pods/log | get, list, delete | onlineboutique-tnt-a, -tnt-b | detect pod state, verify, restart pod, log cho context bundle |
| events | get, list, watch | (như trên) | detect OOMKilled / crash loop |
| deployments | get, list, patch, update | (như trên) | restart, adjust memory |
| deployments/scale | get, update, patch | (như trên) | scale worker |
| secrets, configmaps | get, list, patch, update | (như trên) | cert rotation / env secret (demo) |

**Tuyệt đối KHÔNG**: ClusterAdmin · ClusterRole/RoleBinding edit · IAM modify · namespace ngoài allowlist · delete namespace.

## 5. Telemetry Schema Alignment ⭐

CDO emit được cả 5 signal. Bảng review:

| Signal (AIO generic) | Emit? | Source | Mapping/transform | Field enrich | Used for |
|---|---|---|---|---|---|
| service_error_rate | ✅ yes | Istio/Prometheus (live) · CSV (offline) | error req / total req (sliding 5s) | namespace, deployment | detect + verify |
| service_latency_p95 | ✅ yes | Istio/Prometheus · CSV | p95 latency window | endpoint, namespace, deployment | service stuck |
| container_resource_usage | ✅ yes | cAdvisor/kube-state · CSV | memory working-set / CPU | pod_name, container | OOM/memory leak |
| application_log_event | ✅ yes | CloudWatch/Loki · CSV | filter ERROR/stacktrace | pod_name, level | context bundle |
| distributed_trace_error_event | ✅ yes | Istio→OTel/Jaeger · CSV | span statusCode != 0 | trace_id, span_id, operation | cross-service fault |

Phản hồi 7 câu hỏi telemetry của AIO:
1. **Emit được cả 5**: yes (live qua Istio/Prom/OTel; offline qua CSV preprocessor).
2. **Nguồn**: bảng trên.
3. **Field thiếu**: không thiếu field bắt buộc; lưu ý **không có signal cho cert-expiry / queue-depth** → 2 pattern đó design-only (ADR-006).
4. **Enrich `labels.namespace` + `labels.deployment`**: ✅ yes cho mọi action-able signal.
5. **Tần suất/độ trễ**: error_rate/latency 5s, resource 10s, log/trace on-event; emit p99 < 5-20s (telemetry contract).
6. **Đổi tên field**: dùng top-level `ts, tenant_id, service, signal_name, value` + `labels{}` đúng contract — không cần đổi.
7. **tenant_id UUID offline**: dùng UUID ở mục 0 (tnt-a/tnt-b); RE2/RE3 simulation giữ `tnt-re2-simulation`/`tnt-re3-simulation` khi replay dataset gốc.

Sample payload CDO sẽ emit:
```json
{
  "ts": "2026-06-25T10:30:00.123Z",
  "tenant_id": "a1a1a1a1-0000-4000-8000-000000000001",
  "service": "emailservice",
  "signal_name": "container_resource_usage",
  "value": 503316480,
  "labels": {"system": "OB", "namespace": "onlineboutique-tnt-a",
             "deployment": "emailservice", "pod_name": "emailservice-68d7f5c9b-abcde",
             "container": "main"}
}
```

## 6. Incident Injection Plan ⭐

≥10 scenario = các pattern × 2 tenant × mức độ, chạy trong cửa sổ ≥4h.

| Scenario | How injected | Expected signal | Cleanup | Status |
|---|---|---|---|---|
| Pod OOM | set memory limit thấp / load cao | OOMKilled event, restart_count↑, container_resource_usage↑ | restore memory limit | implement |
| Service stuck | readiness fail / sleep inject | readiness fail, service_latency_p95↑, available replicas↓ | restart deployment | implement |
| Code fault (f1-f5) | replay RE3 dataset / inject error | service_error_rate↑, application_log_event ERROR, trace error | restart / rollback | implement |
| Queue backlog | (design) push jobs vào queue mock | queue_depth↑ (cần thêm signal) | drain queue | design-only |
| Cert expiring | (design) fake secret annotation | cert_expiry_days thấp (cần thêm signal) | reset annotation | design-only |
| Unsafe action case | target namespace forbidden (kube-system) | **blast-radius denied → no action** | — | safety proof |

## 7. Pre-state Snapshot Format

CDO executor snapshot trước action (audit + rollback). Ai lấy: **CDO executor** (Lambda), lưu vào audit S3 theo `correlation_id`.
```json
{
  "snapshot_id": "snap-20260624-001",
  "correlation_id": "<same as cycle>",
  "tenant_id": "a1a1a1a1-0000-4000-8000-000000000001",
  "namespace": "onlineboutique-tnt-a",
  "resource_kind": "Deployment",
  "resource_name": "emailservice",
  "replicas": 2,
  "image": "emailservice:v0.10.0",
  "resources": {"requests": {"cpu": "100m", "memory": "64Mi"},
                "limits": {"cpu": "200m", "memory": "128Mi"}},
  "captured_at": "2026-06-24T10:30:00Z"
}
```

## 8. Audit Storage Interface

- **Store**: S3 `tf-3-cdo2-sandbox-audit-<acct>`, **Object Lock Compliance 90d**, KMS CMK ([`infra/modules/state-audit`](infra/modules/state-audit/main.tf)).
- **Writer**: CDO orchestrator ghi mỗi state (detect/decide/guardrail/execute/verify/escalate/rollback) — single-writer, prefix per-tenant `audit/<tenant_id>/<correlation_id>/`.
- **Query**: **Athena** (SQL) — cấp cho AIO/mentor review.
- **Schema** audit event: theo ví dụ AIO (`audit_id, correlation_id, idempotency_key, tenant_id, event_type, matched_pattern, dry_run_mode, action_plan, safety{}, created_at`) — CDO ghi đủ chuỗi quyết định.

## 9. Verification Metric Source

Phản hồi 5 câu hỏi verify:
1. **Nguồn `post_telemetry_window`**: CDO query Prometheus (live) / trích CSV sau mốc lỗi (offline).
2. **Verify window**: **5 phút** mặc định, configurable per pattern (executor Wait step).
3. **Đủ telemetry theo contract**: yes, đúng form `post_telemetry_window[]`.
4. **Offline map**: mốc "sau action" = các dòng CSV sau timestamp inject lỗi của scenario đó.
5. **Execute fail**: CDO **KHÔNG gọi verify** — chuyển thẳng **rollback + escalate** (executor hiện tại). Nếu AIO muốn vẫn gọi `/v1/verify` với `status=FAILED` để engine quyết, báo để đổi.

## 10. Network/Auth gọi AI engine

- Endpoint `https://ai-engine.tf-3.internal/` (internal ALB, private). SG `cdo-2-platform-sg` → `tf-3-ai-engine-sg:8080`.
- Headers mọi call: `Authorization: IAM SigV4`, `X-Tenant-Id`, `Idempotency-Key` (UUID v4), `X-Request-Id` (UUID v4), `Content-Type: application/json`.
- Client + error handling (400/409/429/503 + fallback) đã sẵn: [`executor/engine_client.py`](executor/engine_client.py).

## 11. Rollback mechanism per action

| Action | Rollback |
|---|---|
| RESTART_DEPLOYMENT | idempotent, không cần rollback (verify lại) |
| SCALE_UP_PODS | restore replica count từ snapshot |
| ADJUST_MEMORY_LIMIT | restore memory limit cũ từ snapshot |
| ROLLBACK (rollout undo) | đã là rollback; verify bắt buộc sau |
| (regression bất kỳ) | executor Auto-Rollback step → restore snapshot → escalate |

## 12. Checklist response

- [x] Cluster topology · [x] Service catalog · [x] Tenant→namespace · [x] Allowed action matrix
- [x] RBAC/ServiceAccount · [x] Telemetry schema + sample · [x] Incident injection · [x] Pre-state snapshot
- [x] Audit interface · [x] Verification source · [x] Rollback per action · [x] Network/auth

## Cần AIO chốt lại (trước freeze)
- Canonical signal names (generic vs Istio) — đề xuất generic.
- Topology graph format (JSON adjacency / OTel / Kiali export).
- Audit writer: single-writer CDO (đề xuất) hay AIO ghi trực tiếp?
- Execute-fail: escalate thẳng (đề xuất) hay vẫn gọi verify với FAILED?
