# W10-D3 — Evidence Pack

Bằng chứng D3 Platform Integration + Runbook + Cost: namespace có guardrail
(ResourceQuota + LimitRange), LimitRange cấp default cho pod thiếu resources,
quota từ chối khi vượt hạn, chaos self-heal, runbook + postmortem, Cost Anomaly
Detection trên AWS.

Môi trường:
- Cluster: minikube (Docker driver)
- AWS: Cost Anomaly Detection qua Terraform (region us-east-1)

## 1. Namespace + guardrail áp dụng

```powershell
kubectl apply -f cloud/w10/day-c/platform-bootstrap/00-namespace.yaml
kubectl apply -f cloud/w10/day-c/platform-bootstrap/resourcequota.yaml
kubectl apply -f cloud/w10/day-c/platform-bootstrap/limitrange.yaml
kubectl -n platform-app get resourcequota,limitrange
```

![ResourceQuota + LimitRange applied](screenshots/01-quota-limitrange.png)

## 2. LimitRange cấp default cho pod thiếu resources

Pod `no-resources` không khai báo resources → LimitRange inject default:

```powershell
kubectl -n platform-app get pod no-resources -o jsonpath='{.spec.containers[0].resources}'
# -> {"limits":{"cpu":"200m","memory":"256Mi"},"requests":{"cpu":"50m","memory":"64Mi"}}
```

![default request/limit được inject](screenshots/02-limitrange-default.png)

## 3. ResourceQuota từ chối khi vượt hạn

`quota-hog` đòi 10 x 512Mi = 5Gi > quota 2Gi → chỉ một số pod tạo được, còn lại
bị từ chối:

```text
Error creating: pods "quota-hog-..." is forbidden: exceeded quota: platform-quota,
requested: requests.memory=512Mi, used: requests.memory=2Gi, limited: requests.memory=2Gi
```

![exceeded quota trong ReplicaSet events](screenshots/03-quota-exceeded.png)

## 4. Chaos — xoá pod, self-heal

```powershell
.\cloud\w10\day-c\chaos\kill-pod.ps1 -Namespace platform-app -Selector app=hog
```

Pod bị xoá → ReplicaSet tạo lại, tổng số Ready quay về như cũ.

![pod mới được tạo lại sau chaos](screenshots/04-chaos-selfheal.png)

## 5. Runbook + Postmortem

Bộ runbook (admission blocking, cluster compromise 6 bước, secret rotation) +
template postmortem blameless.

![runbooks/ trong repo](screenshots/05-runbooks.png)

## 6. AWS Cost Anomaly Detection

```powershell
cd cloud/w10/day-c/cost; terraform apply
```

Monitor theo SERVICE + subscription email ngưỡng USD. Xác nhận trên AWS Console
(Cost Management → Cost Anomaly Detection) và email confirm.

![Cost Anomaly Monitor + Subscription](screenshots/06-cost-anomaly.png)

## Kết luận

- Quota (tổng) + LimitRange (mỗi container) = guardrail tài nguyên trong cluster.
- LimitRange cấp default để pod thiếu khai báo không vỡ vì quota.
- Self-heal chứng minh qua chaos: xoá pod, hệ tự tạo lại.
- Runbook (trước) + postmortem (sau) chuẩn hoá xử lý sự cố.
- Cost Anomaly Detection bắt chi phí AWS bất thường mà quota trong cluster không thấy.
