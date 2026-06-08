# W9 — Lab onsite (T5 11/06 + T6 12/06): GitOps-ify W8 + bolt-on observability + canary

> Đà Nẵng, full day T5 + sáng T6. Show-and-tell 13h30 T6.
> **15h–16h T6: Test 2 (D3 + Lab)**.
> Blueprint chi tiết: [`knowledge/w9-foundation-gitops-observability-canary.md`](../../../knowledge/w9-foundation-gitops-observability-canary.md) §11.

## Mục tiêu

1. Bỏ `kubectl apply` tay → mọi thay đổi qua Git, ArgoCD sync.
2. App W8 (nginx pod-name LB) → expose `/metrics` → Prometheus scrape.
3. SLO 99.5% success → burn rate alert trên Grafana.
4. Deploy v2 = `Rollout` canary 10→30→60→100, AnalysisTemplate auto-abort.

## Layout

```
lab/
├── README.md             # lệnh chạy + sơ đồ + giải thích (commit)
├── EVIDENCE_PACK.md      # screenshot + log + URL (commit)
├── NOTES.md              # PRIVATE — gitignore
├── screenshots/
├── bootstrap/            # ArgoCD install + root App-of-Apps
├── apps/                 # mỗi file = 1 Application
└── manifests/            # nội dung từng app (monitoring/otel/rollouts/demo-api)
```

## Show-and-tell checklist (T6 13h30)

- [ ] `git revert` 1 commit → ArgoCD tự sync → cluster về trạng thái trước (audit qua `git log`)
- [ ] Deploy `:v2-bad` → canary auto-abort tại step 30% → Grafana hiện burn rate spike
- [ ] Deploy `:v2-good` → 4 step pass → promote 100%
- [ ] Show dashboard SLO 99.5% + alert lịch sử

## Sau lab
- [ ] Nếu có resource AWS (managed Prometheus...) → **destroy** lấy evidence xong
- [ ] Cập nhật `reflection.md` ở `cloud/w9/`
