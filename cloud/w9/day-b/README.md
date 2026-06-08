# W9 — Day B (T3 09/06): Observability — SLO/SLI/OTel

> Self-study D2. Scope: OTel SDK + Collector, Prometheus + Grafana + Loki,
> SLO methodology, multi-window burn rate alert (1h×5m fast, 6h×30m slow).
> Tài liệu nền: [`knowledge/w9-foundation-gitops-observability-canary.md`](../../../knowledge/w9-foundation-gitops-observability-canary.md) §5–§7.

## Layout

```
day-b/
├── README.md
├── notes.md
├── NOTES.md              # PRIVATE
├── screenshots/          # Grafana dashboard, alert rule fire
├── otel/                 # collector config thử nghiệm
├── dashboards/           # Grafana dashboard JSON
└── alert-rules/          # PrometheusRule YAML (burn rate)
```

## TODO hôm nay
- [ ] Đọc lý thuyết §5–§7 + Google SRE Workbook (Alerting on SLOs)
- [ ] Cài kube-prometheus-stack qua helm (hoặc ArgoCD App từ D1)
- [ ] Cài OTel Collector, ghép pipeline traces→logs→metrics
- [ ] Viết recording rule + 2 alert (fast/slow) cho SLO 99.9%
- [ ] Tạo Grafana dashboard "SLO + error budget burndown"
- [ ] Bắn lỗi giả (sleep + 500) → xác nhận alert fire trong 5–7 phút
- [ ] Commit `[W9-D2] <topic>`
