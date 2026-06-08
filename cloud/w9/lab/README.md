# W9 — Lab: GitOps-ify W8 platform + bolt-on observability + canary

Mục tiêu:
1. Bỏ `kubectl apply` tay, mọi thay đổi qua Git, ArgoCD sync.
2. App W8 expose `/metrics`, Prometheus scrape.
3. SLO 99.5% success, burn rate alert trên Grafana.
4. Deploy v2 = `Rollout` canary 10→30→60→100, AnalysisTemplate auto-abort.

Blueprint chi tiết: [`knowledge/w9-foundation-gitops-observability-canary.md`](../../../knowledge/w9-foundation-gitops-observability-canary.md) §11.

## Layout

```
lab/
  README.md
  EVIDENCE_PACK.md
  screenshots/
  bootstrap/                  ArgoCD install + root App-of-Apps
  apps/                       Mỗi file = một Application
  manifests/                  Nội dung từng app
                              (monitoring / otel / rollouts / demo-api)
```

## Show-and-tell checklist

- `git revert` một commit → ArgoCD tự sync → cluster về trạng thái trước
  (audit qua `git log`).
- Deploy `:v2-bad` → canary auto-abort tại step 30% → Grafana hiện burn rate
  spike.
- Deploy `:v2-good` → bốn step pass → promote 100%.
- Show dashboard SLO 99.5% + alert lịch sử.
