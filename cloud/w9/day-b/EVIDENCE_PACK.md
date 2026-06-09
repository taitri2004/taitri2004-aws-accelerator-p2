# W9-D2 — Evidence Pack

Bằng chứng đã làm D2 Observability: cài kube-prometheus-stack, scrape app demo
qua ServiceMonitor, định nghĩa SLO + multi-window burn rate alert, sinh lỗi giả
và xác nhận alert chuyển trạng thái inactive → pending → firing.

Môi trường:
- Cluster: minikube (Kubernetes v1.35.1)
- Stack: kube-prometheus-stack (Helm), namespace `monitoring`
- App demo: podinfo 6.7.1, namespace `demo`, expose `http_request_duration_seconds_count{status}`

## 1. Prometheus scrape podinfo (ServiceMonitor hoạt động)

Cả hai pod podinfo được scrape, health = up:

```
podinfo-655dccccfd-ckxsf  health=up  endpoint=http://10.244.0.50:9898/metrics
podinfo-655dccccfd-x4c5n  health=up  endpoint=http://10.244.0.51:9898/metrics
```

## 2. Recording rules đánh giá được

`job:slo_errors:ratio_rate5m` trả về 0 khi không có lỗi (chỉ traffic health
probe 200), xác nhận công thức error ratio đúng.

## 3. Sinh lỗi giả → burn rate vượt ngưỡng → alert firing

Chạy `loadgen.ps1 -ErrorRate 0.8` (gọi `/status/500`). Tiến trình trạng thái
alert `PodinfoErrorBudgetBurnFast` (ngưỡng fast = 14.4 × budget 0.01 = 0.144):

```
[18:39:07] err5m=0      err1h=0      fastAlert=inactive
[18:39:22] err5m=0.269  err1h=0.153  fastAlert=inactive
[18:39:37] err5m=0.269  err1h=0.153  fastAlert=pending
[18:40:37] err5m=0.769  err1h=0.720  fastAlert=pending
[18:41:22] err5m=0.781  err1h=0.742  fastAlert=firing
```

Diễn giải:
- Khi error ratio cả hai cửa sổ (5m và 1h) vượt 0.144, alert vào `pending`.
- Sau `for: 2m` giữ điều kiện, alert chuyển `firing` (lúc 18:41:22).
- Cơ chế multi-window: cả cửa sổ ngắn lẫn dài đều phải vượt ngưỡng mới fire,
  giảm báo nhầm.

## 4. Screenshots

Lưu trong `screenshots/` (bổ sung):
- `01-prometheus-targets-podinfo-up.png` — Prometheus Targets, podinfo up
- `02-grafana-slo-dashboard.png` — dashboard SLO + burn rate vượt ngưỡng
- `03-prometheus-alert-firing.png` — alert PodinfoErrorBudgetBurnFast firing

## Kết luận

- ServiceMonitor (Prometheus Operator) tự động cấu hình scrape, không sửa
  `prometheus.yml` tay.
- SLO định nghĩa bằng recording rule; alert dùng multi-window multi-burn-rate
  theo Google SRE.
- Toàn bộ recording rule + alert khai báo qua `PrometheusRule` CRD, GitOps-friendly.

## Tham chiếu

- Foundation note: [`knowledge/w9-foundation-gitops-observability-canary.md`](../../../knowledge/w9-foundation-gitops-observability-canary.md) §5–§7
- Google SRE — Alerting on SLOs: https://sre.google/workbook/alerting-on-slos
