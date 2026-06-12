# W9 Lab — Ship Smartly (GitOps + Observability + Canary)

Đưa một bản `api` mới ra production an toàn: đổi version qua Git → ArgoCD sync →
canary thả dần → Prometheus/SLO tự chấm → tốt thì lên 100%, tệ thì tự rollback;
SLO vi phạm thì alert về email.

## Yêu cầu

- Docker, kubectl, minikube, git, plugin `kubectl-argo-rollouts`, `kubeconform`.
- `minikube start --cpus=4 --memory=6g --driver=docker`
- ArgoCD pull từ chính repo này (`main`), các Application trỏ vào `cloud/w9/lab/...`.


## Cấu trúc

```
cloud/w9/lab/
  app/                     Flask BE (API JSON /api/*, /metrics; env ERROR_RATE, VERSION)
  k8s/                     web FE: nginx serve trang + reverse proxy /api/ sang BE — sync waves
  k8s-api/
    api.yaml               Rollout (canary + analysis) + Service
    analysis-template.yaml  auto-abort theo success rate (Prometheus)
    servicemonitor.yaml    Prometheus scrape /metrics
    loadgen.yaml           sinh traffic
  monitoring/
    slo-rules.yaml         SLO recording rule + multi-window burn-rate alert
    alertmanager-email.yaml route alert -> email (Gmail SMTP)
  argocd/
    root.yaml              app-of-apps
    apps/                  web.yaml, api.yaml, slo.yaml (mỗi file = 1 Application)
```

CI: `.github/workflows/validate-w9-lab.yml` chạy kubeconform khi mở PR.

---

## Phần A — GitOps

```powershell
minikube start --cpus=4 --memory=6g --driver=docker

# ArgoCD (--server-side vì CRD > 256KB)
kubectl create ns argocd
kubectl apply -n argocd --server-side --force-conflicts `
  -f https://raw.githubusercontent.com/argoproj/argo-cd/stable/manifests/install.yaml
kubectl -n argocd rollout status deploy/argocd-server

# app-of-apps: apply root 1 lần, ArgoCD tự tạo web/api/slo từ Git
kubectl apply -f cloud/w9/lab/argocd/root.yaml
kubectl -n argocd get applications
```

- **Self-heal**: drift thủ công (`kubectl scale ...`) bị ArgoCD kéo về đúng Git.
- **Rollback**: `git revert HEAD --no-edit; git push` → ArgoCD sync về bản cũ.
  `kubectl rollout undo` không ăn vì Git vẫn là version mới (self-heal apply lại).
- **Sync waves** (`k8s/`): Namespace(-1) → ConfigMap(0) → Deployment(1) → Service(2).
  Deployment đọc ConfigMap qua `envFrom`; sai thứ tự thì pod `CreateContainerConfigError`.

---

## Phần B — Observability + Canary

```powershell
# Prometheus stack
helm repo add prometheus-community https://prometheus-community.github.io/helm-charts; helm repo update
helm install kube-prometheus-stack prometheus-community/kube-prometheus-stack -n monitoring --create-namespace `
  --set prometheus.prometheusSpec.serviceMonitorSelectorNilUsesHelmValues=false `
  --set prometheus.prometheusSpec.ruleSelectorNilUsesHelmValues=false

# Argo Rollouts
kubectl create ns argo-rollouts
kubectl apply -n argo-rollouts --server-side --force-conflicts `
  -f https://github.com/argoproj/argo-rollouts/releases/latest/download/install.yaml

# Image cho api (nạp thẳng vào cụm, không cần registry)
docker build -t w9-api:2 cloud/w9/lab/app/
minikube image load w9-api:2
```

`k8s-api/` đã có Rollout `api`, Service, ServiceMonitor — ArgoCD deploy. Kiểm tra
metric tại Prometheus (`flask_http_request_total{namespace="api"}`).

### Web FE + BE

FE (`web`, nginx) serve trang dashboard và reverse proxy `/api/` sang BE (`api`,
Flask) qua DNS nội bộ `api.api.svc.cluster.local:8080` — trình duyệt ở ngoài cụm
không gọi thẳng BE được nên phải đi qua proxy. Trang có 4 chức năng gọi BE:
trạng thái backend (version/pod/uptime, tự refresh), bắn 20 request đo success
rate, echo xử lý chuỗi, bộ đếm lượt thăm theo pod.

```powershell
kubectl -n web port-forward svc/web 18080:80
# mo http://localhost:18080
```

---

## Phần C — Challenge "Ship Smartly"

Đủ 3 yêu cầu:

**1. Auto-abort.** `api.yaml` dùng `strategy.canary.analysis` trỏ template
`success-rate` (`analysis-template.yaml`): query Prometheus mỗi 20s,
`successCondition result >= 0.95`, `failureLimit 1`. Bản lỗi → success rate tụt →
AnalysisRun Failed → Rollout tự abort về stable.

```powershell
# tốt:  VERSION v2, ERROR_RATE 0   -> canary chạy hết -> Healthy
# lỗi:  ERROR_RATE 0.5             -> success rate ~50% -> auto-abort
kubectl argo rollouts get rollout api -n api --watch
```

**2. SLO + alert → email.** `slo-rules.yaml`: SLO 99% (error budget 1%), recording
rule error ratio, multi-window burn-rate alert (fast 1h×5m @14.4x, slow 6h×30m @6x).
`alertmanager-email.yaml`: route alert label `alertgroup=lab` → Gmail SMTP.

```powershell
# app password KHÔNG commit — tạo secret tay:
kubectl -n monitoring create secret generic smtp-secret --from-literal=password=<APP_PASSWORD>
# điền email thật vào alertmanager-email.yaml, commit + push
```

Inject lỗi → burn rate vượt ngưỡng → alert fire → email.

**3. Rollback < 5 phút.** `git revert HEAD --no-edit; git push`.

Bằng chứng (ảnh canary auto-abort + email): `EVIDENCE_PACK.md`.
