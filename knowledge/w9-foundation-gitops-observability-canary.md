# W9 — Foundation: GitOps + Observability + Canary

Kiến thức nền cho W9 "Deliver Smartly", tổng hợp từ tài liệu chính thống:
ArgoCD, OpenGitOps, OpenTelemetry, Google SRE, Argo Rollouts, k6.

## Map nội dung

| Ngày | Chủ đề | Section |
|---|---|---|
| D1 | GitOps & CI/CD | §1 GitOps · §2 ArgoCD · §3 GH Actions · §4 Rollback |
| D2 | Observability + SLO | §5 OTel · §6 Prom/Grafana/Loki · §7 SLI/SLO + burn rate |
| D3 | Progressive Delivery | §8 Argo Rollouts · §9 AnalysisTemplate · §10 k6 |
| Lab | GitOps-ify + bolt-on | §11 Lab blueprint · §12 Ghép với W8 |

---

## §1. Bốn nguyên tắc GitOps (OpenGitOps)

1. **Declarative** — Trạng thái mong muốn khai báo bằng YAML/HCL, không phải script ra lệnh.
2. **Versioned & Immutable** — Lưu trong Git, có lịch sử đầy đủ, không bị sửa lén.
3. **Pulled Automatically** — Agent (ArgoCD/Flux) chạy trong cluster, pull từ Git, không push từ ngoài vào.
4. **Continuously Reconciled** — Agent liên tục so sánh actual với desired, tự sửa drift.

Hệ quả thực tế:
- `kubectl apply` tay = vi phạm GitOps (drift). Mọi thay đổi đi qua PR → merge → sync.
- Cluster bị xoá → re-bootstrap chỉ cần trỏ ArgoCD vào Git repo.
- Audit = `git log`.

Docs: https://opengitops.dev

---

## §2. ArgoCD — core concepts

### 2.1 Kiến trúc
ArgoCD chạy trong namespace `argocd`, gồm 3 component chính:
- **argocd-server** (API + UI)
- **argocd-repo-server** (clone Git, render manifest từ Helm/Kustomize)
- **argocd-application-controller** (reconcile loop: diff Git vs cluster, apply)

### 2.2 `Application` CRD — đơn vị deploy

```yaml
apiVersion: argoproj.io/v1alpha1
kind: Application
metadata:
  name: guestbook
  namespace: argocd
  finalizers:
  - resources-finalizer.argocd.argoproj.io
spec:
  project: default
  source:
    repoURL: https://github.com/example/manifests
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
Một `Application` cha chỉ chứa các Application con (folder `apps/` trong Git
gồm các YAML `kind: Application`). Bootstrap cluster = apply một root App, tất
cả Application con tự pull theo. Chỉ admin nên có quyền sửa repo cha vì root
có thể tạo App tới project bất kỳ.

### 2.4 Sync Phases + Sync Waves
**Phases:** `PreSync` → `Sync` → `PostSync` (hook fail giữa chừng → dừng).
**Waves:** sắp xếp thứ tự trong cùng phase bằng annotation, số nhỏ chạy trước
(cho phép số âm).

```yaml
metadata:
  annotations:
    argocd.argoproj.io/sync-wave: "-1"
    argocd.argoproj.io/hook: PreSync
```

Dùng khi: CRD phải có trước Operator; DB migration trước Deployment; smoke
test sau cùng (PostSync).

Thứ tự điển hình: Namespace `-1` → ConfigMap/Secret `0` → Deployment `1` →
Service `2`. Thiếu wave: Deployment chạy trước ConfigMap nó cần → pod lỗi
`CreateContainerConfigError`.

### 2.5 ApplicationSet
Sinh nhiều App từ một template (theo cluster list, Git folder, list literal).
Phù hợp cho multi-cluster bootstrap.

### 2.6 ArgoCD vs Flux

| Yếu tố | ArgoCD | Flux |
|---|---|---|
| UI | Có (mạnh) | Không có UI mặc định |
| Multi-tenancy | Project + RBAC mạnh | Dùng namespace |
| Image automation | Argo Image Updater | Built-in (`ImageUpdateAutomation`) |
| Cách tiếp cận | UI-first | CLI-first |

Cả hai đều CNCF Graduated. W9 sử dụng ArgoCD theo yêu cầu của chương trình.

Docs: https://argo-cd.readthedocs.io · https://fluxcd.io/flux

### 2.7 Synced ≠ Healthy + ba thao tác (Sync / Self-Heal / Prune)

ArgoCD có **hai trạng thái độc lập**, rất hay nhầm:
- **Synced** — cluster có khớp Git không? (so YAML Git vs cluster). Khớp =
  Synced, lệch = OutOfSync.
- **Healthy** — resource có chạy tốt không? (check Pod status). Chạy = Healthy,
  lỗi = Degraded.

Ví dụ kinh điển: push `image: v2-loi` → ArgoCD apply thành công → **Synced**
nhưng Pod crash → **Degraded**. Synced chỉ nói "đã apply đúng cái Git ghi",
không bảo đảm app chạy được.

Ba thao tác:
| Thao tác | Nghĩa |
|---|---|
| Sync | đưa cluster về khớp Git (apply cái Git có) |
| Self-Heal | sửa cluster tay làm lệch Git → tự kéo về Git (drift remediation) |
| Prune | xoá khỏi Git → xoá khỏi cluster (mặc định tắt, bật `prune: true`) |

---

## §3. GitHub Actions — plan-on-PR / apply-on-merge

Pattern chuẩn cho IaC (Terraform):
- PR mở → workflow chạy `fmt` + `validate` + `plan` → comment plan vào PR.
- PR merge `main` → workflow chạy `apply` (cần env approval cho prod).

### 3.1 Workflow plan-on-PR (skeleton)

```yaml
name: Terraform Plan
on:
  pull_request:
    paths: ['terraform/**']
permissions:
  contents: read
  pull-requests: write
  id-token: write
jobs:
  plan:
    runs-on: ubuntu-latest
    steps:
    - uses: actions/checkout@v4
    - uses: aws-actions/configure-aws-credentials@v4
      with:
        role-to-assume: arn:aws:iam::<ACCOUNT_ID>:role/gha-tf-plan
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
on:
  push:
    branches: [main]
    paths: ['terraform/**']
jobs:
  apply:
    runs-on: ubuntu-latest
    environment: prod
    steps:
    - uses: actions/checkout@v4
    - uses: aws-actions/configure-aws-credentials@v4
      with:
        role-to-assume: arn:aws:iam::<ACCOUNT_ID>:role/gha-tf-apply
        aws-region: ap-southeast-1
    - uses: hashicorp/setup-terraform@v3
    - run: terraform init && terraform apply -auto-approve
      working-directory: terraform
```

### 3.3 OIDC thay static credential
GitHub OIDC issuer + IAM role `AssumeRoleWithWebIdentity`, không cần
`AWS_ACCESS_KEY_ID` trong secrets. Trust policy IAM:

```json
{
  "Federated": "arn:aws:iam::<ACCOUNT_ID>:oidc-provider/token.actions.githubusercontent.com",
  "Action": "sts:AssumeRoleWithWebIdentity",
  "Condition": {
    "StringEquals": {
      "token.actions.githubusercontent.com:sub": "repo:<OWNER>/<REPO>:ref:refs/heads/main"
    }
  }
}
```

Docs: https://docs.github.com/en/actions/deployment/security-hardening-your-deployments/about-security-hardening-with-openid-connect

### 3.4 CI cho manifest K8s + Branch Protection

Với GitOps thuần (manifest K8s, không Terraform), CI chỉ **validate**, KHÔNG
apply — ArgoCD lo phần apply (CD). Phân vai rõ: **CI = gác cổng, CD = ArgoCD**.

```yaml
name: validate
on: { pull_request: { paths: ["k8s/**"] } }
jobs:
  validate:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - run: kubeconform -strict -summary k8s/
```

- **kubeconform** check manifest đúng schema K8s; sai schema → CI đỏ.
- **Branch Protection** (GitHub → Settings → Branches → rule `main`) là lớp ép
  buộc làm GitOps thực sự an toàn:
  - Require a pull request before merging (+ approvals)
  - Require status checks to pass → chọn `validate`
  - No bypassing (admin cũng không push thẳng)
  → Không ai push thẳng `main`; mọi thay đổi qua PR + review + CI xanh.

---

## §4. Rollback — `git revert` vs `kubectl rollout undo`

| | `git revert <sha>` (GitOps) | `kubectl rollout undo` (imperative) |
|---|---|---|
| Nguồn sự thật | Git | Cluster (sẽ drift) |
| Audit | PR mới, history rõ | Không log ở Git |
| Khi nào dùng | Default cho mọi rollback | Emergency, sau đó phải sync lại Git ngay |
| Lịch sử | Git history vĩnh viễn | Mất sau ~10 revisions, không có message |
| Tốc độ | 1–3 phút (ArgoCD poll) | Tức thì |
| Rủi ro | Có thể revert kèm config khác → conflict | Bị selfHeal ghi đè → rollback giả |

**Vì sao `kubectl rollout undo` là "rollback giả" dưới GitOps:** Git vẫn ghi
version lỗi (vd v2). Undo về v1 → cluster lệch Git → ArgoCD selfHeal thấy
OutOfSync → apply lại v2 → cluster quay về version lỗi sau vài giây. Chỉ
`git revert` (sửa nguồn sự thật) mới rollback thật. Trade-off: chậm 1–3 phút
nhưng an toàn + có audit.

Quy tắc: GitOps strict chỉ revert. Nếu phải undo cấp cứu thì tắt auto-sync,
undo, sửa Git, bật lại sync.

---

## §5. OpenTelemetry — 3 signals + Collector pipeline

### 5.1 Ba signal
- **Traces** — chuỗi span theo request qua nhiều service (distributed tracing).
- **Metrics** — số đo theo thời gian (counter, gauge, histogram).
- **Logs** — event có timestamp.

### 5.2 SDK vs Collector
- **SDK** = library nhúng vào app (auto-instrument hoặc manual span). Sinh
  telemetry, export ra collector qua OTLP.
- **Collector** = service đứng giữa, theo pattern **Receiver → Processor →
  Exporter**. App không cần biết backend cụ thể; đổi backend
  (Prometheus/Tempo/Loki) chỉ cần đổi config Collector.

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
    endpoint: 0.0.0.0:8889
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

### 5.4 Auto-instrument cho K8s
OpenTelemetry Operator inject sidecar/init-container, set ENV
`OTEL_EXPORTER_OTLP_ENDPOINT=http://otel-collector:4317`, app tự gửi.

Docs: https://opentelemetry.io/docs

---

## §6. Prometheus + Grafana + Loki

### 6.1 Prometheus
- **Pull model** — scrape `/metrics` (OpenMetrics format) từ target.
- **PromQL** — query language. Bốn loại metric: Counter, Gauge, Histogram, Summary.
- **Recording rule** — pre-compute query nặng thành metric mới.
- **Alerting rule** — bắn alert khi expr đúng trong `for: duration`.

```promql
sum(rate(http_requests_total{status=~"5.."}[5m]))
  /
sum(rate(http_requests_total[5m]))
```

### 6.2 Grafana
Dashboard + datasource (Prometheus/Loki/Tempo). Variable `$service`,
panel time-series/stat/heatmap. Provisioning = nhồi dashboard qua YAML
(GitOps-friendly).

### 6.3 Loki — khác Elasticsearch
- **Index chỉ label**, không index nội dung, chi phí lưu trữ thấp hơn ES.
- **Push** model (agent Promtail/Alloy → Loki), khác Prometheus pull.
- **LogQL** kế thừa cú pháp PromQL.

```logql
{app="api", env="prod"} |= "error" | json | status >= 500
rate({app="api"} |= "panic" [5m])
{namespace="argocd"} |~ "(?i)reconciliation failed"
```

Docs: https://prometheus.io/docs · https://grafana.com/docs/loki/latest

---

## §7. SLI / SLO / SLA + multi-window burn rate

### 7.1 Định nghĩa (Google SRE Book ch.4)
- **SLI** — số đo (vd: % request HTTP 2xx, p99 latency).
- **SLO** — target cho SLI (vd: 99.9% trong 30 ngày).
- **SLA** — hợp đồng với khách hàng kèm penalty nếu miss SLO. SLA luôn lỏng hơn
  SLO (buffer cho team).

### 7.2 Error budget
SLO 99.9% trong 30 ngày cho phép `0.1% × 30 × 24 × 60 = 43.2 phút` lỗi.
Hết budget thì dừng release feature, tập trung fix bug + tăng reliability.

### 7.3 Multi-window multi-burn-rate alert
**Vấn đề** đơn window: chọn dài (1h) → react chậm; chọn ngắn (5m) → noisy.
**Giải pháp** kết hợp hai window cùng phải fail:
- **Page nhanh**: long 1h + short 5m, burn rate 14.4× (tiêu 2% budget trong 1h).
- **Page chậm**: long 6h + short 30m, burn rate 6× (tiêu 5% budget trong 6h).
- **Ticket**: long 3d + short 6h, burn rate 1×.

Quy tắc: short window = long window / 12.

```yaml
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

Docs: https://sre.google/sre-book/service-level-objectives · https://sre.google/workbook/alerting-on-slos

---

## §8. Argo Rollouts — Canary CRD

### 8.1 Tại sao không dùng Deployment
`Deployment` chỉ rolling update theo `maxSurge/maxUnavailable`, không có:
- Pause giữa các step.
- Traffic split chính xác (chỉ ratio replica).
- Analysis tự động abort khi metric tệ.

Argo Rollouts thay thế `Deployment` bằng `Rollout` CRD, giữ nguyên ReplicaSet
và Service.

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
      canaryService: api-canary
      stableService: api-stable
      trafficRouting:
        nginx: { stableIngress: api-ingress }
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

### 8.4 CLI thường dùng

```powershell
kubectl argo rollouts get rollout api -w
kubectl argo rollouts promote api
kubectl argo rollouts abort api
kubectl argo rollouts set image api api=myrepo/api:v3
```

Docs: https://argoproj.github.io/argo-rollouts

---

## §9. AnalysisTemplate — auto-abort canary

### 9.1 Khái niệm
- **AnalysisTemplate** — template (tái dùng, có `args`).
- **AnalysisRun** — instance chạy thật, kết quả Successful / Failed / Inconclusive.
- **Background** chạy song song toàn bộ rollout; **Inline** chạy như một step, block.

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
    successCondition: result[0] >= 0.99
    failureLimit: 2
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
Thay vì `success-rate` thuần, query trực tiếp burn rate giống §7.3:

```yaml
successCondition: result[0] < 14.4
```

Canary auto-abort dùng cùng metric với alert page, đảm bảo reliability nhất quán.

### 9.4 Background analysis

```yaml
strategy:
  canary:
    analysis:
      templates: [{ templateName: success-rate }]
      startingStep: 2
    steps:
    - setWeight: 10
    - pause: { duration: 2m }
    - setWeight: 50
```

Docs: https://argoproj.github.io/argo-rollouts/features/analysis

---

## §10. k6 — load test trong CI

### 10.1 Script structure

```javascript
import http from 'k6/http';
import { check, sleep } from 'k6';

export const options = {
  stages: [
    { duration: '30s', target: 20 },
    { duration: '1m',  target: 20 },
    { duration: '20s', target: 0 },
  ],
  thresholds: {
    http_req_failed:   ['rate<0.01'],
    http_req_duration: ['p(95)<300'],
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
k6 run --out experimental-prometheus-rw load.js
```

### 10.3 Dùng cho canary
Trong lab W9: trong khi canary chạy step, CI bắn k6, Prometheus thu metric,
AnalysisTemplate đọc, quyết định promote hoặc abort.

Docs: https://grafana.com/docs/k6/latest · alternative: https://github.com/tsenart/vegeta

---

## §11. Lab blueprint — "GitOps-ify W8 + bolt-on observability + canary"

### 11.1 Mục tiêu
1. Bỏ `kubectl apply` tay, mọi thay đổi qua Git, ArgoCD sync.
2. App W8 expose `/metrics`, Prometheus scrape.
3. SLO 99.5% success, burn rate alert trên Grafana.
4. Deploy v2 = `Rollout` canary 10→30→60→100 với analysis Prometheus auto-abort.

### 11.2 Repo layout đề xuất

```
cloud/w9/lab/
  README.md
  EVIDENCE_PACK.md
  bootstrap/
    argocd-install.yaml
    root-app.yaml
  apps/
    monitoring.yaml
    otel.yaml
    rollouts.yaml
    demo-api.yaml
  manifests/
    monitoring/
    otel-collector/
    argo-rollouts/
    demo-api/
      rollout.yaml
      service-stable.yaml
      service-canary.yaml
      analysis-template/
        success-rate.yaml
```

### 11.3 Sequence install (1-time)

```powershell
minikube status
# nếu stop: minikube start

kubectl create namespace argocd
kubectl apply -n argocd --server-side --force-conflicts -f https://raw.githubusercontent.com/argoproj/argo-cd/stable/manifests/install.yaml

$b64 = kubectl -n argocd get secret argocd-initial-admin-secret -o jsonpath="{.data.password}"
[Text.Encoding]::UTF8.GetString([Convert]::FromBase64String($b64))

kubectl port-forward -n argocd svc/argocd-server 18080:443

kubectl apply -f cloud/w9/lab/bootstrap/root-app.yaml
```

### 11.4 Show-and-tell checklist
- `git revert` một commit → ArgoCD tự sync → cluster về trạng thái trước.
- Deploy `:v2-bad` (lỗi 50% 5xx) → canary tự abort tại step 30% → Grafana hiện burn rate spike.
- Deploy `:v2-good` → 4 step pass → promote 100%.
- Show dashboard SLO 99.5% + alert lịch sử.

---

## §12. Ghép với W8

| W8 đã có | W9 ghép |
|---|---|
| minikube cluster | App W9 deploy đè lên, không xoá cluster |
| Terraform IaC | GitHub Actions tf-plan-on-PR áp vào folder `cloud/w8/exercise` |
| SSM thay SSH | OIDC GH→AWS (§3.3) cùng triết lý: bỏ static secret |
| `.gitignore` Terraform | Giữ nguyên cho W9 |
| Commit `[W8-Dx]` | `[W9-Dx]`, push hằng ngày T2–T4 |

Cảnh báo tái sử dụng:
- PowerShell `>` UTF-16: ghi YAML/JSON dùng `[IO.File]::WriteAllText`.
- minikube docker driver không tự lộ port: cần `minikube tunnel` hoặc NodePort + `minikube service`.
- ArgoCD `Application` có CRD chưa kịp tạo → fail: dùng sync wave -1 cho CRD install.
- Cài ArgoCD bằng `kubectl apply` thường lỗi `applicationsets` CRD vượt 262KB
  annotation limit: phải dùng `kubectl apply --server-side --force-conflicts`.
- Port 8080 trên Windows có thể nằm trong excluded port range (HTTP.sys),
  dùng port khác như 18080 cho port-forward.

---

## §13. Cheatsheet command

```powershell
argocd login localhost:18080
argocd app list
argocd app sync demo-api
argocd app history demo-api
argocd app rollback demo-api <rev>

kubectl argo rollouts get rollout api -w
kubectl argo rollouts promote api
kubectl argo rollouts abort api
kubectl argo rollouts dashboard

kubectl -n monitoring port-forward svc/kube-prometheus-stack-prometheus 9090
kubectl -n monitoring port-forward svc/kube-prometheus-stack-grafana    3000

k6 run --vus 20 --duration 60s load.js
k6 run --out experimental-prometheus-rw load.js
```

LogQL ví dụ:
```logql
{namespace="argocd"} |= "level=error"
rate({app="demo-api"} |~ "5\\d\\d" [1m])
```

---

## §14. Tài liệu tham khảo

**GitOps & CI/CD**
- ArgoCD — https://argo-cd.readthedocs.io
- OpenGitOps — https://opengitops.dev
- GitHub Actions — https://docs.github.com/en/actions
- Flux — https://fluxcd.io/flux

**Observability**
- OpenTelemetry — https://opentelemetry.io/docs
- Prometheus — https://prometheus.io/docs
- Grafana — https://grafana.com/docs/grafana/latest
- Loki — https://grafana.com/docs/loki/latest
- Google SRE Book ch.4 — https://sre.google/sre-book/service-level-objectives
- SRE Workbook — Implementing SLOs — https://sre.google/workbook/implementing-slos
- SRE Workbook — Alerting on SLOs — https://sre.google/workbook/alerting-on-slos

**Progressive Delivery**
- Argo Rollouts — https://argoproj.github.io/argo-rollouts
- Flagger — https://flagger.app
- CNCF Progressive Delivery — https://www.cncf.io/blog/2024/01/26/progressive-delivery

**Load test**
- k6 — https://grafana.com/docs/k6/latest
- Vegeta — https://github.com/tsenart/vegeta
