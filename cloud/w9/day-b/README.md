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
  values/
    kube-prometheus-stack-values.yaml   Helm values (gọn cho minikube)
  otel/
    collector-config.yaml               OTel Collector config
    collector-deployment.yaml           Collector Deployment + ServiceMonitor
    telemetrygen-deployment.yaml        Sinh metric OTLP test
  manifests/podinfo/                    App demo + ServiceMonitor
  alert-rules/
    slo-burn-rate.yaml                  PrometheusRule: recording + burn rate
  dashboards/
    podinfo-slo-dashboard.json          Grafana dashboard SLO
  loadgen.ps1                           Sinh lỗi giả để kích alert
```

## Các bước

1. Cài helm (binary về user dir nếu choco cần admin).
2. `helm install kube-prometheus-stack` vào namespace `monitoring` với values.
3. Deploy podinfo + ServiceMonitor (namespace `demo`).
4. Apply PrometheusRule (recording rules + burn rate alerts).
5. Import dashboard `podinfo-slo` vào Grafana.
6. Chạy `loadgen.ps1` sinh lỗi → xem alert fire + burn rate spike trên dashboard.
7. Deploy OTel Collector + telemetrygen → xác nhận metric `gen` chảy qua collector
   vào Prometheus.

## Lệnh chính

```powershell
$h = "$env:USERPROFILE\tools\helm\helm.exe"

kubectl create namespace monitoring
& $h repo add prometheus-community https://prometheus-community.github.io/helm-charts
& $h repo update
& $h install kube-prometheus-stack prometheus-community/kube-prometheus-stack `
  --namespace monitoring --values cloud/w9/day-b/values/kube-prometheus-stack-values.yaml

kubectl apply -f cloud/w9/day-b/manifests/podinfo/
kubectl apply -f cloud/w9/day-b/alert-rules/slo-burn-rate.yaml

kubectl -n monitoring port-forward svc/kube-prometheus-stack-grafana 3000:80
kubectl -n monitoring port-forward svc/kube-prometheus-stack-prometheus 9090:9090

kubectl -n demo port-forward svc/podinfo 9898:9898
.\cloud\w9\day-b\loadgen.ps1 -ErrorRate 0.6 -DurationSec 600
```

OTel Collector (pipeline OTLP → prometheus exporter → Prometheus):

```powershell
kubectl apply -f cloud/w9/day-b/otel/collector-config.yaml
kubectl apply -f cloud/w9/day-b/otel/collector-deployment.yaml
kubectl apply -f cloud/w9/day-b/otel/telemetrygen-deployment.yaml

kubectl -n monitoring port-forward svc/otel-collector 8889:8889
curl.exe -s http://localhost:8889/metrics | Select-String "^gen"
```

Prometheus UI: `Status > Targets` kiểm tra `serviceMonitor/monitoring/otel-collector`
ở trạng thái UP, sau đó query `gen`.

Grafana mặc định: user `admin`, password `admin` (đặt trong values, đổi nếu cần).

Chi tiết bằng chứng xem `EVIDENCE_PACK.md`.
