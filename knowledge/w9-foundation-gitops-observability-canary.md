# W9 — Foundation: GitOps + Observability + Canary

> Kiến thức nền cho W9 "Deliver Smartly" — tổng hợp từ tài liệu chính thống
> (ArgoCD, OpenGitOps, OpenTelemetry, Google SRE, Argo Rollouts, k6).
> Mục tiêu: đọc file này là đủ làm self-study D1–D3 + lab onsite + Test 1/2.
> Cập nhật: 08/06/2026.

---

## Map W9 → file này

| Ngày | Chủ đề | Đọc section |
|---|---|---|
| T2 08/06 — D1 | GitOps & CI/CD | §1 GitOps · §2 ArgoCD · §3 GH Actions · §4 Rollback |
| T3 09/06 — D2 | Observability + SLO | §5 OTel · §6 Prom/Grafana/Loki · §7 SLI/SLO + burn rate |
| T4 10/06 — D3 | Progressive Delivery | §8 Argo Rollouts · §9 AnalysisTemplate · §10 k6 |
| T5–T6 — Lab | GitOps-ify W8 + bolt-on | §11 Lab blueprint + §12 ghép với W8 |

**Test 1 (T4 17h):** scope D1 + D2 → ôn §1–§7.
**Test 2 (T6 15h):** scope D3 + Lab → ôn §8–§12.

---

## §1. 4 nguyên tắc GitOps (OpenGitOps)

1. **Declarative** — Trạng thái mong muốn (desired state) khai báo bằng YAML/HCL, không phải script ra lệnh.
2. **Versioned & Immutable** — Lưu trong Git, có lịch sử đầy đủ, không bị sửa lén.
3. **Pulled Automatically** — Agent (ArgoCD/Flux) chạy trong cluster, **pull** từ Git, không ai push từ ngoài vào.
4. **Continuously Reconciled** — Agent liên tục so sánh actual ↔ desired, tự sửa drift.

**Hệ quả thực tế:**
- `kubectl apply` tay = **vi phạm GitOps** (drift). Mọi thay đổi đi qua PR → merge → sync.
- Cluster bị xoá → re-bootstrap chỉ cần trỏ ArgoCD vào Git repo.
- Audit = `git log`.

📚 https://opengitops.dev

---

## §2. ArgoCD — core concepts

### 2.1 Kiến trúc
ArgoCD chạy như namespace `argocd` trong cluster, có 3 component chính:
- **argocd-server** (API + UI)
- **argocd-repo-server** (clone Git, render manifest từ Helm/Kustomize)
- **argocd-application-controller** (reconcile loop — diff Git vs cluster, apply)

### 2.2 `Application` CRD — đơn vị deploy

```yaml
apiVersion: argoproj.io/v1alpha1
kind: Application
metadata:
  name: guestbook
  namespace: argocd
  finalizers:
  - resources-finalizer.argocd.argoproj.io   # xoá App → xoá luôn resource
spec:
  project: default
  source:
    repoURL: https://github.com/me/manifests
    targetRevision: HEAD
    path: apps/guestbook
  destination:
    server: https://kubernetes.default.svc
    namespace: guestbook
  syncPolicy:
    automated:
      prune: true       # xoá resource khi Git xoá
      selfHeal: true    # revert drift tay
    syncOptions:
    - CreateNamespace=true
```

### 2.3 App-of-Apps pattern
Một `Application` cha **chỉ chứa các Application con** (folder `apps/` trong Git toàn YAML kind: Application). Bootstrap cluster = apply 1 root App, tất cả tự pull theo.

⚠️ Chỉ admin nên có quyền sửa repo cha (vì root có thể tạo App tới project bất kỳ).

### 2.4 Sync Phases + Sync Waves
**Phases:** `PreSync` → `Sync` → `PostSync` (hook fail giữa chừng → dừng).
**Waves:** sắp xếp thứ tự trong cùng phase bằng annotation, số nhỏ chạy trước (cho phép số âm).

```yaml
metadata:
  annotations:
    argocd.argoproj.io/sync-wave: "-1"   # DB migration chạy trước app
    argocd.argoproj.io/hook: PreSync
```

**Dùng khi:** CRD phải có trước Operator; DB migration trước Deployment; Smoke test sau cùng (PostSync).

### 2.5 ApplicationSet
Sinh nhiều App từ 1 template (theo cluster list, Git folder, list literal…). Khuyến nghị cho multi-cluster bootstrap.

### 2.6 ArgoCD vs Flux (chọn cái nào?)

| Yếu tố | ArgoCD | Flux |
|---|---|---|
| UI | Có (mạnh) | Không (cần Weave GitOps) |
| Multi-tenancy | Project + RBAC mạnh | Yếu hơn, dùng namespace |
| Image automation | Cần plugin / Image Updater | Built-in (`ImageUpdateAutomation`) |
| Learning curve | Dễ vào nhờ UI | CLI-first |
| Cộng đồng VN | Phổ biến hơn | Ít gặp |

→ W9 dùng **ArgoCD** (theo announcement).

📚 https://argo-cd.readthedocs.io · https://fluxcd.io/flux

---

## §3. GitHub Actions — plan-on-PR / apply-on-merge

**Pattern chuẩn cho IaC (Terraform):**
- PR mở → workflow chạy `fmt` + `validate` + `plan` → comment plan vào PR.
- PR merge `main` → workflow chạy `apply` (cần env approval cho prod).

### 3.1 Workflow plan-on-PR (skeleton)

```yaml
# .github/workflows/tf-plan.yml
name: Terraform Plan
on:
  pull_request:
    paths: ['terraform/**']
permissions:
  contents: read
  pull-requests: write   # để comment plan
  id-token: write        # OIDC → AWS (không hardcode key)
jobs:
  plan:
    runs-on: ubuntu-latest
    steps:
    - uses: actions/checkout@v4
    - uses: aws-actions/configure-aws-credentials@v4
      with:
        role-to-assume: arn:aws:iam::749043157095:role/gha-tf-plan
        aws-region: ap-southeast-1
    - uses: hashicorp/setup-terraform@v3
    - run: terraform init
      working-directory: terraform
    - run: terraform fmt -check
    - run: terraform validate
    - id: plan
      run: terraform plan -no-color -out=tf.plan
    - uses: actions/github-script@v7
      with:
        script: |
          github.rest.issues.createComment({
            issue_number: context.issue.number,
            owner: context.repo.owner,
            repo: context.repo.repo,
            body: '```\n' + `${{ steps.plan.outputs.stdout }}` + '\n```'
          })
```

### 3.2 Apply-on-merge

```yaml
# .github/workflows/tf-apply.yml
on:
  push:
    branches: [main]
    paths: ['terraform/**']
jobs:
  apply:
    runs-on: ubuntu-latest
    environment: prod      # gate manual approval ở GH env settings
    steps:
    - uses: actions/checkout@v4
    - uses: aws-actions/configure-aws-credentials@v4
      with:
        role-to-assume: arn:aws:iam::749043157095:role/gha-tf-apply
        aws-region: ap-southeast-1
    - uses: hashicorp/setup-terraform@v3
    - run: terraform init && terraform apply -auto-approve
      working-directory: terraform
```

### 3.3 OIDC thay static key (best practice 2026)
GitHub OIDC issuer + IAM role `AssumeRoleWithWebIdentity` → **không cần** `AWS_ACCESS_KEY_ID` trong secrets. Trust policy IAM:

```json
{
  "Federated": "arn:aws:iam::749043157095:oidc-provider/token.actions.githubusercontent.com",
  "Action": "sts:AssumeRoleWithWebIdentity",
  "Condition": {
    "StringEquals": {
      "token.actions.githubusercontent.com:sub": "repo:taitri2004/taitri2004-aws-accelerator-p2:ref:refs/heads/main"
    }
  }
}
```

📚 https://docs.github.com/en/actions/deployment/security-hardening-your-deployments/about-security-hardening-with-openid-connect

---

## §4. Rollback — `git revert` vs `kubectl rollout undo`

| | `git revert <sha>` (GitOps way) | `kubectl rollout undo` (imperative) |
|---|---|---|
| Nguồn sự thật | Git | Cluster (sẽ drift) |
| Audit | PR mới, history rõ | Không log ở Git |
| Khi nào dùng | **Default** cho mọi rollback | Emergency only — sau đó **phải** sync lại Git ngay |
| Risk | Có thể revert kèm config khác → conflict | Drift → ArgoCD selfHeal có thể "roll forward" lại |

**Quy tắc:** GitOps strict → chỉ revert. Nếu phải undo cấp cứu → tắt auto-sync, undo, sửa Git, bật lại sync.

---

## §5. OpenTelemetry — 3 signals + Collector pipeline

### 5.1 3 signals
- **Traces** — chuỗi span theo request qua nhiều service (distributed tracing).
- **Metrics** — số đo theo thời gian (counter, gauge, histogram).
- **Logs** — event có timestamp.

### 5.2 SDK vs Collector
- **SDK** = library nhúng vào app (auto-instrument hoặc manual span). Sinh telemetry, export ra collector qua OTLP.
- **Collector** = service đứng giữa, **Receiver → Processor → Exporter**. Lợi: app không cần biết backend (Prometheus/Tempo/Loki) — đổi backend, đổi config Collector là xong.

### 5.3 Collector config tối thiểu

```yaml
receivers:
  otlp:
    protocols:
      grpc: { endpoint: 0.0.0.0:4317 }
      http: { endpoint: 0.0.0.0:4318 }

processors:
  batch: {}
  memory_limiter:
    check_interval: 1s
    limit_mib: 400

exporters:
  prometheus:
    endpoint: 0.0.0.0:8889   # Prometheus scrape ở đây
  loki:
    endpoint: http://loki:3100/loki/api/v1/push
  otlp/tempo:
    endpoint: tempo:4317
    tls: { insecure: true }

service:
  pipelines:
    metrics: { receivers: [otlp], processors: [memory_limiter, batch], exporters: [prometheus] }
    logs:    { receivers: [otlp], processors: [memory_limiter, batch], exporters: [loki] }
    traces:  { receivers: [otlp], processors: [memory_limiter, batch], exporters: [otlp/tempo] }
```

### 5.4 Auto-instrument cho K8s (operator)
OTel Operator inject sidecar/init-container, ENV `OTEL_EXPORTER_OTLP_ENDPOINT=http://otel-collector:4317` → app tự gửi.

📚 https://opentelemetry.io/docs

---

## §6. Prometheus + Grafana + Loki — quick map

### 6.1 Prometheus
- **Pull model** — scrape `/metrics` (OpenMetrics format) từ target.
- **PromQL** — query language. 4 loại metric: Counter, Gauge, Histogram, Summary.
- **Recording rule** — pre-compute query nặng thành metric mới (vd `job:slo_errors_per_request:ratio_rate5m`).
- **Alerting rule** — bắn alert khi expr đúng `for: duration`.

```promql
# rate request 5xx trên tổng request, 5 phút
sum(rate(http_requests_total{status=~"5.."}[5m]))
  /
sum(rate(http_requests_total[5m]))
```

### 6.2 Grafana
Dashboard + datasource (Prometheus/Loki/Tempo). Variable `$service`, panel time-series/stat/heatmap. **Provisioning** = nhồi dashboard qua YAML (GitOps-friendly).

### 6.3 Loki — khác Elasticsearch
- **Index chỉ label**, không index nội dung → rẻ hơn ES ~10x.
- **Push** model (agent Promtail/Alloy → Loki). Khác Prometheus pull.
- **LogQL** kiểu PromQL.

```logql
{app="api", env="prod"} |= "error" | json | status >= 500
rate({app="api"} |= "panic" [5m])          # convert log → metric
{namespace="argocd"} |~ "(?i)reconciliation failed"
```

📚 https://prometheus.io/docs · https://grafana.com/docs/loki/latest

---

## §7. SLI / SLO / SLA + multi-window burn rate

### 7.1 Định nghĩa (Google SRE Book ch.4)
- **SLI** — số đo (vd: % request HTTP 2xx, p99 latency).
- **SLO** — target cho SLI (vd: 99.9% trong 30 ngày).
- **SLA** — hợp đồng với khách hàng, kèm penalty $$$ nếu miss SLO. **SLA luôn lỏng hơn SLO** (buffer cho team).

> "Nếu ai nói 'SLA violation' thì 99% trường hợp họ đang nói SLO." — SRE Book.

### 7.2 Error budget
SLO 99.9% / 30 ngày → cho phép `0.1% × 30d × 24h × 60m = 43.2 phút` lỗi.
Hết budget → **dừng release feature**, chỉ fix bug + tăng reliability.

### 7.3 Multi-window multi-burn-rate alert
**Vấn đề** đơn window: chọn dài (1h) → react chậm; chọn ngắn (5m) → noisy.
**Giải pháp** kết hợp **2 window cùng phải fail**:
- **Page nhanh** (sự cố đang diễn ra): long 1h + short 5m, burn rate 14.4× → tiêu 2% budget trong 1h.
- **Page chậm** (kéo dài): long 6h + short 30m, burn rate 6× → tiêu 5% budget trong 6h.
- **Ticket** (rò rỉ chậm): long 3d + short 6h, burn rate 1×.

**Quy tắc:** short = long / 12.

```yaml
# Recording rules
groups:
- name: slo
  rules:
  - record: job:slo_errors:ratio_rate5m
    expr: sum(rate(http_requests_total{status=~"5.."}[5m]))
         / sum(rate(http_requests_total[5m]))
  - record: job:slo_errors:ratio_rate1h
    expr: sum(rate(http_requests_total{status=~"5.."}[1h]))
         / sum(rate(http_requests_total[1h]))
  - record: job:slo_errors:ratio_rate30m
    expr: sum(rate(http_requests_total{status=~"5.."}[30m]))
         / sum(rate(http_requests_total[30m]))
  - record: job:slo_errors:ratio_rate6h
    expr: sum(rate(http_requests_total{status=~"5.."}[6h]))
         / sum(rate(http_requests_total[6h]))

# Alert rules — SLO target 99.9% → error budget 0.001
- name: slo-alerts
  rules:
  - alert: ErrorBudgetBurnFast
    expr: |
      job:slo_errors:ratio_rate1h  > (14.4 * 0.001)
      and
      job:slo_errors:ratio_rate5m  > (14.4 * 0.001)
    for: 2m
    labels: { severity: page }
  - alert: ErrorBudgetBurnSlow
    expr: |
      job:slo_errors:ratio_rate6h  > (6 * 0.001)
      and
      job:slo_errors:ratio_rate30m > (6 * 0.001)
    for: 15m
    labels: { severity: page }
```

📚 https://sre.google/sre-book/service-level-objectives · https://sre.google/workbook/alerting-on-slos

---

## §8. Argo Rollouts — Canary CRD

### 8.1 Vì sao không dùng Deployment?
`Deployment` chỉ làm rolling update theo `maxSurge/maxUnavailable` — không có:
- Pause giữa các step
- Traffic split chính xác (chỉ ratio replica)
- Analysis tự động abort khi metric tệ

→ Argo Rollouts thay thế `Deployment` bằng `Rollout` CRD, **giữ nguyên ReplicaSet + Service**.

### 8.2 Rollout với canary steps

```yaml
apiVersion: argoproj.io/v1alpha1
kind: Rollout
metadata: { name: api }
spec:
  replicas: 10
  selector: { matchLabels: { app: api } }
  template:
    metadata: { labels: { app: api } }
    spec:
      containers:
      - name: api
        image: myrepo/api:v2
  strategy:
    canary:
      canaryService: api-canary    # service trỏ tới canary RS
      stableService: api-stable    # service trỏ tới stable RS
      trafficRouting:
        nginx: { stableIngress: api-ingress }   # hoặc istio/alb
      steps:
      - setWeight: 10
      - pause: { duration: 2m }
      - analysis:
          templates:
          - templateName: success-rate
          args:
          - name: service-name
            value: api-canary
      - setWeight: 30
      - pause: { duration: 2m }
      - setWeight: 60
      - pause: { duration: 5m }
      - setWeight: 100
```

### 8.3 Argo Rollouts vs Flagger

| | Argo Rollouts | Flagger |
|---|---|---|
| Project | Argo (CNCF) | Flux (CNCF) |
| Cách dùng | Thay `Deployment` → `Rollout` CRD | Giữ `Deployment`, thêm `Canary` CR |
| UI | Có (kubectl-argo-rollouts dashboard) | Không (Grafana only) |
| Hợp với | ArgoCD | Flux |

→ W9 = ArgoCD → **Argo Rollouts**.

### 8.4 CLI thường dùng

```powershell
kubectl argo rollouts get rollout api -w        # watch
kubectl argo rollouts promote api               # bỏ qua pause
kubectl argo rollouts abort api                 # huỷ → quay lại stable
kubectl argo rollouts set image api api=myrepo/api:v3
```

📚 https://argoproj.github.io/argo-rollouts

---

## §9. AnalysisTemplate — auto-abort canary

### 9.1 Khái niệm
- **AnalysisTemplate** = template (tái dùng, có `args`).
- **AnalysisRun** = instance chạy thật, kết quả: **Successful / Failed / Inconclusive**.
- **Background** = chạy song song toàn bộ rollout; **Inline** = chạy như 1 step, block.

### 9.2 Mẫu success-rate qua Prometheus

```yaml
apiVersion: argoproj.io/v1alpha1
kind: AnalysisTemplate
metadata: { name: success-rate }
spec:
  args:
  - name: service-name
  metrics:
  - name: success-rate
    interval: 1m
    count: 5
    successCondition: result[0] >= 0.99   # 99% success
    failureLimit: 2                       # 2 lần fail liên tiếp → abort
    provider:
      prometheus:
        address: http://prometheus.monitoring:9090
        query: |
          sum(rate(http_requests_total{
            service="{{args.service-name}}", status!~"5.."}[2m]))
          /
          sum(rate(http_requests_total{
            service="{{args.service-name}}"}[2m]))
```

### 9.3 Ghép canary với burn rate alert
Thay vì `success-rate` thuần, query luôn **burn rate** giống §7.3:

```yaml
successCondition: result[0] < 14.4    # burn rate < ngưỡng page
```

→ Canary auto-abort dùng **cùng metric** ops dùng để page → reliability nhất quán.

### 9.4 Background analysis (chạy suốt)
```yaml
strategy:
  canary:
    analysis:
      templates: [{ templateName: success-rate }]
      startingStep: 2     # bắt đầu analysis từ step 2
    steps:
    - setWeight: 10
    - pause: { duration: 2m }
    - setWeight: 50
    ...
```

📚 https://argoproj.github.io/argo-rollouts/features/analysis

---

## §10. k6 — load test trong CI

### 10.1 Script structure

```javascript
// load.js
import http from 'k6/http';
import { check, sleep } from 'k6';

export const options = {
  stages: [
    { duration: '30s', target: 20 },   // ramp up
    { duration: '1m',  target: 20 },   // steady
    { duration: '20s', target: 0 },    // ramp down
  ],
  thresholds: {
    http_req_failed:   ['rate<0.01'],          // <1% lỗi
    http_req_duration: ['p(95)<300'],          // p95 < 300ms
  },
};

export default function () {
  const res = http.get('http://api.example.com/');
  check(res, { 'status 200': (r) => r.status === 200 });
  sleep(1);
}
```

### 10.2 Chạy + output Prometheus
```powershell
k6 run load.js
# hoặc xuất metric ra Prometheus remote write cho dashboard
k6 run --out experimental-prometheus-rw load.js
```

### 10.3 Dùng cho canary
Trong lab W9: trong khi canary chạy step → CI bắn k6 → Prometheus thu metric → AnalysisTemplate đọc → quyết định promote/abort.

📚 https://grafana.com/docs/k6/latest · alt: https://github.com/tsenart/vegeta

---

## §11. Lab blueprint — "GitOps-ify W8 + bolt-on observability + canary"

### 11.1 Mục tiêu
1. Bỏ `kubectl apply` tay → mọi thay đổi qua Git, ArgoCD sync.
2. App W8 (nginx pod-name LB) → expose `/metrics` (hoặc OTel auto) → Prometheus scrape.
3. SLO 99.5% success → burn rate alert trên Grafana.
4. Deploy v2 = `Rollout` canary 10→30→60→100 với analysis Prometheus auto-abort.

### 11.2 Repo layout đề xuất

```
cloud/w9/lab/
├── README.md                       # lệnh chạy + sơ đồ + giải thích
├── EVIDENCE_PACK.md                # bằng chứng (screenshot, log, link)
├── NOTES.md                        # PRIVATE, gitignore
├── bootstrap/
│   ├── argocd-install.yaml         # ArgoCD core
│   └── root-app.yaml               # App-of-Apps trỏ vào apps/
├── apps/                           # mỗi file = 1 Application
│   ├── monitoring.yaml             # → manifests/monitoring (kube-prom-stack + loki)
│   ├── otel.yaml                   # → manifests/otel-collector
│   ├── rollouts.yaml               # → manifests/argo-rollouts
│   └── demo-api.yaml               # → manifests/demo-api (Rollout + Service)
├── manifests/
│   ├── monitoring/                 # values cho kube-prometheus-stack
│   │   ├── kustomization.yaml
│   │   ├── slo-rules.yaml          # recording + burn rate rules (§7.3)
│   │   └── dashboard-cm.yaml       # Grafana dashboard provisioning
│   ├── otel-collector/
│   ├── argo-rollouts/
│   └── demo-api/
│       ├── rollout.yaml
│       ├── service-stable.yaml
│       ├── service-canary.yaml
│       └── analysis-template.yaml
└── .github/workflows/
    ├── manifest-validate.yml       # kubeconform + kustomize build trên PR
    └── load-test.yml               # k6 chạy khi label `canary` trên PR
```

### 11.3 Sequence install (1-time)

```powershell
# 1) bật minikube cluster W8
minikube status; if (-not $?) { minikube start }

# 2) cài ArgoCD core
kubectl create namespace argocd
kubectl apply -n argocd -f https://raw.githubusercontent.com/argoproj/argo-cd/stable/manifests/install.yaml

# 3) lấy password admin
$pwd = kubectl -n argocd get secret argocd-initial-admin-secret -o jsonpath="{.data.password}"
[Text.Encoding]::UTF8.GetString([Convert]::FromBase64String($pwd))

# 4) port-forward UI
kubectl port-forward -n argocd svc/argocd-server 8080:443

# 5) apply root App-of-Apps → tự cài hết
kubectl apply -f cloud/w9/lab/bootstrap/root-app.yaml
```

### 11.4 Show-and-tell checklist (T6 13h30)
- [ ] `git revert` 1 commit → ArgoCD tự sync → cluster về trạng thái trước (demo audit).
- [ ] Deploy `:v2-bad` (lỗi 50% 5xx) → canary tự abort tại step 30% → Grafana hiện burn rate spike.
- [ ] Deploy `:v2-good` → 4 step pass → promote 100%.
- [ ] Show dashboard SLO 99.5% + alert lịch sử.

---

## §12. Ghép với bài học W8 (tránh giẫm chân)

| W8 đã có | W9 ghép thế nào |
|---|---|
| minikube cluster, app nginx pod-name LB | App W9 deploy đè lên, **đừng `minikube delete`** |
| Terraform IaC (use_lockfile, modules) | GitHub Actions tf-plan-on-PR (§3) áp vào folder `cloud/w8/exercise` được luôn |
| SSM thay SSH | OIDC GH→AWS (§3.3) cùng triết lý: bỏ static secret |
| `NOTES.md` gitignore, `EVIDENCE_PACK.md` commit | Giữ nguyên cho W9 |
| `[W8-Dx]` commit | → `[W9-Dx]`, push hằng ngày T2–T4 |
| Lab `force_destroy=true` cho S3 state | W9 lab chỉ trong cluster local → không tốn $; nếu push metric ra AWS Managed Prometheus thì **destroy sau lab** |

**Cảnh báo đã rút từ W8 tái dùng:**
- PowerShell `>` UTF-16 → ghi YAML/JSON dùng `[IO.File]::WriteAllText`.
- minikube docker driver KHÔNG tự lộ port → cần `minikube tunnel` hoặc NodePort + `minikube service`.
- ArgoCD `Application` có CRD chưa kịp tạo → fail. Dùng **sync wave -1** cho CRD install.

---

## §13. Cheatsheet — lệnh hay dùng

```powershell
# ArgoCD
argocd login localhost:8080
argocd app list
argocd app sync demo-api
argocd app history demo-api
argocd app rollback demo-api <rev>

# Argo Rollouts
kubectl argo rollouts get rollout api -w
kubectl argo rollouts promote api
kubectl argo rollouts abort api
kubectl argo rollouts dashboard         # localhost:3100

# Prometheus / Grafana port-forward
kubectl -n monitoring port-forward svc/kube-prometheus-stack-prometheus 9090
kubectl -n monitoring port-forward svc/kube-prometheus-stack-grafana    3000

# k6
k6 run --vus 20 --duration 60s load.js
k6 run --out experimental-prometheus-rw load.js

# Loki/LogQL quick (qua Grafana Explore)
{namespace="argocd"} |= "level=error"
rate({app="demo-api"} |~ "5\\d\\d" [1m])
```

---

## §14. Reference (tài liệu chính thống — bookmark)

**GitOps & CI/CD**
- ArgoCD — https://argo-cd.readthedocs.io
- OpenGitOps — https://opengitops.dev
- GitHub Actions — https://docs.github.com/en/actions
- Flux (alt) — https://fluxcd.io/flux

**Observability**
- OpenTelemetry — https://opentelemetry.io/docs
- Prometheus — https://prometheus.io/docs
- Grafana — https://grafana.com/docs/grafana/latest
- Loki — https://grafana.com/docs/loki/latest
- Google SRE Book ch.4 — https://sre.google/sre-book/service-level-objectives
- SRE Workbook — Implementing SLOs — https://sre.google/workbook/implementing-slos
- SRE Workbook — Alerting on SLOs (burn rate) — https://sre.google/workbook/alerting-on-slos

**Progressive Delivery**
- Argo Rollouts — https://argoproj.github.io/argo-rollouts
- Flagger (alt) — https://flagger.app
- CNCF Progressive Delivery — https://www.cncf.io/blog/2024/01/26/progressive-delivery

**Load test**
- k6 — https://grafana.com/docs/k6/latest
- Vegeta — https://github.com/tsenart/vegeta
