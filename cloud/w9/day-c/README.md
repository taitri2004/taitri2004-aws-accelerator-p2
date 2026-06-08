# W9 — Day C: Progressive Delivery (Canary)

Scope D3: Argo Rollouts, Rollout CRD, AnalysisTemplate với Prometheus query,
abort criteria, ghép với burn rate.
Tài liệu nền: [`knowledge/w9-foundation-gitops-observability-canary.md`](../../../knowledge/w9-foundation-gitops-observability-canary.md) §8–§10.

## Layout

```
day-c/
  README.md
  notes.md
  EVIDENCE_PACK.md
  screenshots/
  rollout/                    Rollout CRD YAML
  analysis-template/          AnalysisTemplate YAML
```

## Nội dung

1. Cài Argo Rollouts controller + `kubectl argo rollouts` plugin.
2. Convert Deployment → Rollout với canary 10→30→60→100.
3. Viết AnalysisTemplate success-rate qua Prometheus.
4. Demo deploy `:v2-bad` cố tình lỗi → canary auto-abort tại step 30%.
5. Demo deploy `:v2-good` → bốn step pass → promote 100%.
