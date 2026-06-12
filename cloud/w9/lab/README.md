# W9 Lab — Ship Smartly (GitOps + Observability + Canary)

Lab xuyên suốt 2 buổi W9 và kết bằng Challenge "Ship Smartly":

- Buổi sáng (GitOps): Lab 0–7 — quản cụm bằng Git qua ArgoCD.
- Buổi chiều (Observability + Canary): Lab 1–4 — đo SLO, thả canary.
- Challenge: bản mới ra an toàn + tự bảo vệ (auto-abort) + alert SLO về email.

Mục tiêu cuối: đổi version qua Git → canary thả dần → metric/SLO tự chấm →
tốt thì 100%, tệ thì tự rollback; SLO vi phạm thì alert gửi email.

## Yêu cầu

- Docker, kubectl, minikube, git, plugin `kubectl-argo-rollouts`, `kubeconform`.
- Stack khá nặng: `minikube start -p w9 --cpus=4 --memory=6g --driver=docker`.
- Repo GitOps = chính repo này; ArgoCD pull từ `main`, các Application trỏ vào
  `cloud/w9/lab/...`.

## Cấu trúc

```
cloud/w9/lab/
  k8s/                         # web app (Lab 0/3/6) — sync waves
    namespace.yaml             #   Namespace web        (wave -1)
    web.yaml                   #   ConfigMap(0) Deploy(1) Service(2)
  app/                         # Flask api (Lab chiều 2)
    app.py                     #   / có ERROR_RATE, VERSION; /metrics, /healthz
    Dockerfile
  k8s-api/                     # api workload (Lab chiều 3-4 + Challenge)
    api.yaml                   #   Rollout (canary + analysis) + Service
    servicemonitor.yaml        #   Prometheus scrape /metrics
    analysis-template.yaml     #   [Challenge] auto-abort theo success rate
    loadgen.yaml               #   sinh traffic để metric có dữ liệu
  monitoring/                  # [Challenge] đo lường
    slo-rules.yaml             #   SLO recording + multi-window burn-rate alert
    alertmanager-email.yaml    #   route alert -> email (Gmail SMTP)
  argocd/
    root.yaml                  # app-of-apps (Lab sáng 5)
    apps/                      #   web, kube-prometheus-stack, argo-rollouts, api, slo
```

CI: `.github/workflows/validate-w9-lab.yml` (kubeconform) ở repo root — Lab sáng 7.

---

## Phần A — Buổi sáng: GitOps (Lab 0–7)

### Lab 0 — cụm + app trên Git
```powershell
minikube start -p w9 --cpus=4 --memory=6g --driver=docker
kubectl config use-context w9
```
App `web` đã nằm trong Git ở `k8s/` (nginx + ConfigMap + Service). Chưa apply tay.

### Lab 1 — cài ArgoCD
```powershell
kubectl create ns argocd
kubectl apply -n argocd --server-side --force-conflicts `
  -f https://raw.githubusercontent.com/argoproj/argo-cd/stable/manifests/install.yaml
kubectl -n argocd rollout status deploy/argocd-server
```
(`--server-side` vì CRD ArgoCD > 256KB.)

### Lab 2 — Application → ArgoCD tự sync
Application `web` nằm ở `argocd/apps/web.yaml` (source `cloud/w9/lab/k8s`, dest ns
`web`). Lab 5 sẽ để root apply hộ; nếu muốn thử riêng:
```powershell
kubectl apply -f cloud/w9/lab/argocd/apps/web.yaml
kubectl -n argocd get app web        # Synced/Healthy
kubectl -n web get deploy,pod        # 2 pod web
```

### Lab 3 — sync qua Git + self-heal
```powershell
# sửa k8s/web.yaml replicas 2->4, commit + push -> ArgoCD tự kéo
kubectl -n web scale deploy/web --replicas=9   # drift
kubectl -n web get deploy web -w               # vài giây sau selfHeal kéo về Git
```

### Lab 4 — rollback bằng git revert
```powershell
git revert HEAD --no-edit; git push      # ArgoCD sync cụm về commit cũ
```
`kubectl rollout undo` KHÔNG ăn: Git vẫn version mới -> selfHeal apply lại (rollback giả).

### Lab 5 — app-of-apps
```powershell
kubectl apply -f cloud/w9/lab/argocd/root.yaml   # LẦN CUỐI dùng kubectl tạo app
kubectl -n argocd get applications
# lab-root + web + kube-prometheus-stack + argo-rollouts + api + slo
```
Từ giờ thêm app = thả file vào `argocd/apps/` + push, root tự đẻ.

### Lab 6 — sync waves
`k8s/web.yaml` apply theo thứ tự: Namespace(-1) → ConfigMap(0) → Deployment(1) →
Service(2). Deployment đọc ConfigMap qua `envFrom`; thiếu wave thì pod lỗi
`CreateContainerConfigError`. Pod `web` Running = wave đúng thứ tự.

### Lab 7 — CI validate + branch protection
`.github/workflows/validate-w9-lab.yml` chạy `kubeconform -strict` trên manifest
khi mở PR. Sai schema → CI đỏ → chặn merge. Bật Branch Protection cho `main`
(Settings → Branches): require PR review + require status check `validate-w9-lab`.

---

## Phần B — Buổi chiều: Observability + Canary (Lab 1–4)

### Lab 1 — cài Prometheus + Argo Rollouts qua GitOps
Đã khai báo sẵn 2 Helm Application trong `argocd/apps/` (kube-prometheus-stack,
argo-rollouts). Root (Lab sáng 5) tự cài. Verify:
```powershell
kubectl -n monitoring get pods       # prometheus, grafana, alertmanager
kubectl -n argo-rollouts get pods    # rollouts controller
```

### Lab 2 — Flask api có /metrics → build image
```powershell
docker build -t w9-api:1 cloud/w9/lab/app/
minikube image load w9-api:1 -p w9          # nạp ảnh vào cụm, không cần registry
minikube image ls -p w9 | Select-String w9-api
```

### Lab 3 — Rollout + ServiceMonitor → Prometheus thấy metric
`k8s-api/` đã có Rollout `api` (4 replica, image `w9-api:1`), Service, ServiceMonitor.
Root tự deploy. Sinh traffic bằng `loadgen.yaml` (đã kèm). Verify:
```powershell
kubectl -n monitoring port-forward svc/kube-prometheus-stack-prometheus 9090:9090
# Prometheus > Targets: serviceMonitor/api UP
# Query: flask_http_request_total{namespace="api"}  -> tăng dần
```

### Lab 4 — canary (bản này đã nâng lên auto-abort cho Challenge)
Đổi version qua Git rồi theo dõi:
```powershell
# sửa k8s-api/api.yaml: VERSION "v1" -> "v2", commit + push
kubectl argo rollouts get rollout api -n demo --watch   # -n api
```
Slide chiều dừng ở promote/abort tay (`pause: {}` + `kubectl argo rollouts
promote|abort`). Lab này đã thay bằng `AnalysisTemplate` (Challenge) để máy tự
quyết — xem Phần C.

---

## Phần C — Challenge "Ship Smartly"

Đề: đưa bản mới `api` ra an toàn + tự bảo vệ. Phải đủ 4:

1. Mọi thay đổi qua Git, ArgoCD Synced (no drift), reproduce được từ Git;
   `git revert` rollback < 5 phút.
2. 1 SLO + 1 alert fire **về email cá nhân** khi inject lỗi.
3. Canary **bản lỗi tự abort** về bản cũ (quan trọng nhất).

### 1. Auto-abort (đã cấu hình)
`k8s-api/api.yaml` dùng `strategy.canary.analysis` trỏ `success-rate`
(`analysis-template.yaml`): query Prometheus mỗi 20s, `successCondition
result>=0.95`, `failureLimit 1`. Bản lỗi → success rate tụt → AnalysisRun Failed
→ Rollout tự abort, revert stable.

Demo:
```powershell
# bản tốt: VERSION v2, ERROR_RATE 0  -> canary chạy hết -> Healthy
# bản lỗi: ERROR_RATE "0.5"          -> success rate ~50% -> auto-abort
#   (sửa env trong k8s-api/api.yaml, commit + push, hoặc set image/env qua plugin)
kubectl argo rollouts get rollout api -n api --watch
```

### 2. SLO + alert → email
`monitoring/slo-rules.yaml`: SLO 99% (error budget 1%), recording rule cho error
ratio, multi-window burn-rate alert (fast 1h×5m ngưỡng 14.4x, slow 6h×30m ngưỡng 6x).
`monitoring/alertmanager-email.yaml`: route alert có label `alertgroup=lab` tới
email qua Gmail SMTP.

Cấu hình email (app password KHÔNG commit):
```powershell
# 1) tạo secret chứa Gmail app password (16 ký tự, không phải mật khẩu thường)
kubectl -n monitoring create secret generic smtp-secret --from-literal=password=<APP_PASSWORD>
# 2) điền email thật vào monitoring/alertmanager-email.yaml (3 chỗ REPLACE_WITH_YOUR_EMAIL)
#    rồi commit + push -> ArgoCD sync
```
Inject lỗi (ERROR_RATE cao) → burn rate vượt ngưỡng → alert fire → email về hộp thư.

### 3. Rollback < 5 phút
```powershell
git revert HEAD --no-edit; git push      # ArgoCD sync về bản cũ
```

### Nộp
- Repo: Rollout + AnalysisTemplate + SLO/alert, tất cả qua Git.
- README này (giải thích query & ngưỡng).
- Ảnh/clip: canary auto-abort + alert email + rollback. Xem `EVIDENCE_PACK.md`.

---

## 3 mảnh ghép

```
GitOps (đổi qua Git, tự sync) -> Observability (SLO chấm khỏe/bệnh) -> Canary (thả dần, tệ auto-abort)
```
