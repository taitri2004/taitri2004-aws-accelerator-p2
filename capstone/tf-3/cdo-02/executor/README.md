# Self-Heal Executor (CDO-02) — local skeleton

Executor phía CDO: nhận alert → gọi AI engine (`/v1/detect` → `/v1/decide` → execute → `/v1/verify`) với **safety gate** (confidence · blast-radius · action allow-list · forbidden-namespace · payload guard · idempotency · circuit breaker) + audit + escalate. Angle **K8s-heavy** (ADR-001): executor đóng gói thành **Deployment chạy trong cluster** (in-cluster SA, no kubeconfig); optional wrap **Argo Workflows** W12.

**pattern_type:** `urgent` → apply trực tiếp K8s API · `deferred` → tạo PR GitOps (không ghi thẳng cluster).
**Outcomes:** `NO_ANOMALY · RESOLVED · DRY_RUN · DEFERRED_GITOPS · DUPLICATE_SKIPPED · RETRY · ESCALATED · FALLBACK_STATIC_RUNBOOK · BAD_REQUEST`.
**Action cho phép (5):** RESTART_DEPLOYMENT, PATCH_MEMORY_LIMIT, SCALE_REPLICAS, ROLLOUT_UNDO, ROTATE_SECRET. **DELETE_POD bị cấm** → escalate.

## Mục đích skeleton này
- **Hôm nay**: test code path với `mock_engine.py` (local), trước cả khi AIO giao mock API.
- **Mai**: trỏ `ENGINE_BASE_URL` vào mock API của AIO → verify integration thật.

## Chạy

```bash
pip install -r requirements.txt

# Terminal 1: chạy mock engine local (contract-compliant)
python mock_engine.py            # listen :8080

# Terminal 2: chạy 1 vòng remediation demo
python -m orchestrator           # gọi mock, in audit ra stdout

# Hoặc test tự động
pytest -q
```

## Trỏ vào mock API của AIO (mai)

```bash
export ENGINE_BASE_URL="http://ai-engine.self-heal-system.svc.cluster.local:8080"  # service in-cluster (CDO tự host)
export TENANT_ID="6c8b4b2b-4d45-4209-a1b4-4b532d56a31c"     # cdo-2 UUID (deployment §2.C)
export AUTH_MODE="local_trust"  # local_trust (in-cluster, NetworkPolicy) | sigv4 (legacy)
export AWS_REGION="us-east-1"   # cho IRSA gọi AWS services (S3/DDB/Bedrock)
python -m orchestrator
```

> Bộ test tích hợp đập API thật: xem [`integration/`](integration/) (`probe_endpoints.py`, `run_e2e.py`, `probe_errors.py`) — local & AWS xài chung, chỉ đổi `ENGINE_BASE_URL`.
> Lưu ý Windows: port 8080 hay bị chặn → mock engine dùng `MOCK_PORT` khác (vd 8540).

## Deploy lên cluster (W12, K8s-heavy)
| Bước orchestration | File | Triển khai in-cluster |
|---|---|---|
| Detect / Decide / Verify | `engine_client.py` | gọi engine (Local Trust in-cluster, NetworkPolicy) |
| Dry-run gate · Blast-radius · Circuit breaker | `guardrails.py` | logic trong pod |
| Execute / Rollback (kubectl) | `executor.py` | **`load_incluster_config()`** + in-cluster SA |
| Idempotency lock | `guardrails.py` | DynamoDB (IRSA) |
| Audit write (S3 Object Lock) | `audit.py` | S3 (IRSA) |
| Choice DONE/RETRY/ROLLBACK/ESCALATE | `orchestrator.py` | loop trong Deployment |

→ Đóng gói `Dockerfile` + `manifests/platform/executor-deployment.yaml` (IRSA SA). Optional: wrap Argo Workflows (mỗi bước = 1 step).

## ⚠️ Còn chốt với AIO (critical, trước integration T3 W12)
- **Hosting**: contract vẫn ghi "shared backend ECS, 2 CDO chung endpoint" — phải đổi thành "mỗi CDO tự host trên platform mình" (rubric chấm chỗ này).
- **Bedrock**: engine dùng Claude 3 Haiku — nếu CDO tự host thì ai cấp `bedrock:InvokeModel` + chịu $50/ngày? Demo W12 chạy Bedrock thật hay ép rule-based?
- **DELETE_POD / forbidden_namespaces**: review nói "thêm", contract thật "gỡ/chưa có" — chốt cuối để khoá allow/deny.
- Topology/tracing format (P7) — chưa có trong contract.
