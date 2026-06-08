# W9 — Day C (T4 10/06): Progressive Delivery — Canary

> Self-study D3 (sáng). Scope: Argo Rollouts, Rollout CRD, AnalysisTemplate với
> Prometheus query, abort criteria, ghép với burn rate.
> **15h–17h: LIVE Minh Observability** · **17h–18h: Test 1 (D1+D2)**.
> Tài liệu nền: [`knowledge/w9-foundation-gitops-observability-canary.md`](../../../knowledge/w9-foundation-gitops-observability-canary.md) §8–§10.

## Layout

```
day-c/
├── README.md
├── notes.md
├── NOTES.md              # PRIVATE — có cả note Test 1
├── screenshots/          # rollout dashboard, canary abort evidence
├── rollout/              # Rollout CRD YAML
└── analysis-template/    # AnalysisTemplate YAML
```

## TODO hôm nay
- [ ] Đọc lý thuyết §8–§10 trước 15h
- [ ] Cài Argo Rollouts controller + kubectl plugin
- [ ] Convert Deployment cũ → Rollout với canary 4 step (10→30→60→100)
- [ ] Viết AnalysisTemplate success-rate qua Prometheus query
- [ ] Demo: deploy ":v2-bad" cố tình lỗi → canary auto-abort tại step 30%
- [ ] Demo: deploy ":v2-good" → 4 step pass → promote 100%
- [ ] 15h–17h tham gia live mentor Minh — ghi note vào `NOTES.md`
- [ ] 17h–18h Test 1 — scope D1+D2 (xem `knowledge/w9-foundation-*.md` §1–§7)
- [ ] Commit `[W9-D3] <topic>`
