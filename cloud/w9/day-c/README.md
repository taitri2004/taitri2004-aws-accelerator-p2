# W9 — Day C: Progressive Delivery (Canary)

Scope D3: Argo Rollouts, Rollout CRD, AnalysisTemplate với Prometheus query,
abort criteria, ghép với burn rate.
Tài liệu nền: [`knowledge/w9-foundation-gitops-observability-canary.md`](../../../knowledge/w9-foundation-gitops-observability-canary.md) §8–§10.

Tận dụng D2: AnalysisTemplate query lại metric podinfo trong Prometheus đã dựng
ở day-b (namespace `monitoring` + `demo`).

## Layout

```
day-c/
  README.md
  EVIDENCE_PACK.md
  screenshots/
  rollout/
    podinfo-rollout.yaml        Rollout + Service + ServiceMonitor
  analysis-template/
    success-rate.yaml           AnalysisTemplate query Prometheus
  loadgen-incluster.yaml        Load generator chạy trong cluster
```

## Các bước

1. Cài Argo Rollouts controller (namespace `argo-rollouts`) + plugin kubectl.
2. Apply AnalysisTemplate + Rollout (app `podinfo-canary`, namespace `demo`).
3. Sinh traffic vào `podinfo-canary` để Prometheus có metric đo.
4. Demo GOOD: đổi image → canary 25→50→75→100, analysis pass → promote.
5. Demo BAD: đổi image, đẩy lỗi trong lúc canary → analysis fail → auto-abort.

## Lệnh chính

Cài controller + plugin:

```powershell
kubectl create namespace argo-rollouts
kubectl apply -n argo-rollouts --server-side --force-conflicts `
  -f https://github.com/argoproj/argo-rollouts/releases/latest/download/install.yaml
```

Plugin kubectl: tải `kubectl-argo-rollouts-windows-amd64`, đổi tên thành
`kubectl-argo-rollouts.exe`, đưa vào PATH.

Apply manifests + sinh traffic sạch (load generator chạy trong cluster, bền hơn
port-forward khi pod canary churn):

```powershell
kubectl apply -f cloud/w9/day-c/analysis-template/success-rate.yaml
kubectl apply -f cloud/w9/day-c/rollout/podinfo-rollout.yaml
kubectl apply -f cloud/w9/day-c/loadgen-incluster.yaml
kubectl argo rollouts get rollout podinfo-canary -w
```

Load generator hit ClusterIP `podinfo-canary:9898` qua biến môi trường `TARGET`:
`/` trả 200 (traffic sạch), `/status/500` trả 500 (mô phỏng version lỗi).

Demo GOOD — canary pass, promote:

```powershell
kubectl argo rollouts set image podinfo-canary podinfo=ghcr.io/stefanprodan/podinfo:6.7.0
```

Demo BAD — đẩy lỗi trong lúc canary, analysis fail, auto-abort:

```powershell
kubectl argo rollouts set image podinfo-canary podinfo=ghcr.io/stefanprodan/podinfo:6.6.2
kubectl -n demo set env deploy/canary-load TARGET=/status/500
```

Đưa traffic về sạch sau demo:

```powershell
kubectl -n demo set env deploy/canary-load TARGET=/
```

Chi tiết bằng chứng xem `EVIDENCE_PACK.md`.
