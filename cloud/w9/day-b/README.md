# W9 — Day B: Observability (SLO/SLI/OTel)

Scope D2: OpenTelemetry SDK + Collector, Prometheus + Grafana + Loki, SLO
methodology, multi-window burn rate alert (1h × 5m fast, 6h × 30m slow).
Tài liệu nền: [`knowledge/w9-foundation-gitops-observability-canary.md`](../../../knowledge/w9-foundation-gitops-observability-canary.md) §5–§7.

## Layout

```
day-b/
  README.md
  notes.md
  EVIDENCE_PACK.md
  screenshots/
  otel/                       OpenTelemetry Collector config
  dashboards/                 Grafana dashboard JSON
  alert-rules/                PrometheusRule cho burn rate
```

## Nội dung

1. Cài kube-prometheus-stack qua Helm hoặc ArgoCD Application.
2. Cài OpenTelemetry Collector, cấu hình pipeline traces / logs / metrics.
3. Viết recording rule + hai alert (fast / slow) cho SLO 99.9%.
4. Tạo Grafana dashboard SLO + error budget burndown.
5. Bắn lỗi giả để xác nhận alert fire.
