# W10 — Day C: Platform Integration + Runbook + Cost Guard

Scope D3: tích hợp stack W8→W10 (mini platform < 2h), ResourceQuota + LimitRange,
chaos test, runbook + postmortem, AWS Cost Anomaly Detection.
Tài liệu nền: [`knowledge/w10-foundation-rbac-secrets-platform.md`](../../../knowledge/w10-foundation-rbac-secrets-platform.md) §13–§17.

Tinh thần: ghép mọi thứ thành một platform dựng lại được, có guardrail tài nguyên
+ chi phí và quy trình xử lý sự cố.

## Layout

```
day-c/
  README.md
  notes.md                    Ghi chú self-study D3
  EVIDENCE_PACK.md            Bằng chứng (screenshot + log)
  screenshots/
  platform-bootstrap/
    00-namespace.yaml         ns platform-app (Pod Security restricted)
    resourcequota.yaml        Hạn mức tổng namespace
    limitrange.yaml           Default + min/max mỗi container
    bootstrap.md              Thứ tự dựng W8→W10 < 2h + checklist nghiệm thu
    test/                     pod-no-resources (nhận default) + over-quota (reject)
  runbooks/
    runbook-template.md
    runbook-admission-blocking.md
    runbook-cluster-compromise.md   IR 6 bước, 5 phút đầu
    runbook-secret-rotation.md
    postmortem-template.md
  chaos/
    chaos.md                  Giả thuyết + steady-state
    kill-pod.ps1              Chaos đơn giản (xoá pod, xem self-heal)
    podchaos.yaml             Chaos Mesh (tuỳ chọn)
  cost/                       Terraform: AWS Cost Anomaly Detection
```

CI: `.github/workflows/validate-w10-day-c.yml` (kubeconform + terraform validate).

## Mục tiêu D3 (acceptance)

| # | Yêu cầu | Artifact |
|---|---|---|
| 1 | Tích hợp W8→W10, bootstrap < 2h | `platform-bootstrap/bootstrap.md` |
| 2 | ResourceQuota + LimitRange | `platform-bootstrap/resourcequota.yaml` + `limitrange.yaml` |
| 3 | Quota từ chối vượt hạn / LimitRange cấp default | `platform-bootstrap/test/` |
| 4 | Chaos test self-heal | `chaos/kill-pod.ps1` + `chaos.md` |
| 5 | Runbook + postmortem template | `runbooks/` |
| 6 | AWS Cost Anomaly Detection | `cost/` (Terraform) |

## Run

```powershell
# Guardrail tài nguyên
kubectl apply -f cloud/w10/day-c/platform-bootstrap/00-namespace.yaml
kubectl apply -f cloud/w10/day-c/platform-bootstrap/resourcequota.yaml
kubectl apply -f cloud/w10/day-c/platform-bootstrap/limitrange.yaml
kubectl apply -f cloud/w10/day-c/platform-bootstrap/test/pod-no-resources.yaml   # nhận default
kubectl apply -f cloud/w10/day-c/platform-bootstrap/test/over-quota-deploy.yaml  # 1 phần bị reject
kubectl -n platform-app get resourcequota platform-quota

# Chaos
.\cloud\w10\day-c\chaos\kill-pod.ps1 -Namespace platform-app -Selector app=hog

# Cost (AWS, cần credentials)
cd cloud/w10/day-c/cost; terraform init; terraform apply
```

Bằng chứng: `EVIDENCE_PACK.md`. Bẫy khi chạy thật: `notes.md` §5.
