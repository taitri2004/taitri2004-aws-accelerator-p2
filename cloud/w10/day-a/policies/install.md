# Cài Gatekeeper lên minikube

OPA Gatekeeper chạy như Validating Admission Webhook trong namespace
`gatekeeper-system`.

```powershell
# Cài qua manifest chính thống (server-side vì CRD lớn)
kubectl apply --server-side --force-conflicts `
  -f https://raw.githubusercontent.com/open-policy-agent/gatekeeper/release-3.17/deploy/gatekeeper.yaml

kubectl -n gatekeeper-system rollout status deploy/gatekeeper-controller-manager
kubectl -n gatekeeper-system rollout status deploy/gatekeeper-audit
```

Apply policy theo đúng thứ tự — **template trước, constraint sau** (constraint là
instance của CRD do template sinh ra; apply ngược sẽ lỗi `no matches for kind`):

```powershell
# 1. ConstraintTemplate (sinh ra các CRD K8sRequiredLabels, ...)
kubectl apply -f cloud/w10/day-a/policies/templates/

# Đợi CRD sẵn sàng (~5-10s)
kubectl get constrainttemplates

# 2. Constraint (instance)
kubectl apply -f cloud/w10/day-a/policies/constraints/

# 3. (tuỳ chọn) ValidatingAdmissionPolicy native — không cần Gatekeeper
kubectl apply -f cloud/w10/day-a/policies/vap/
```

Kiểm tra trạng thái + số vi phạm (audit):

```powershell
kubectl get constraints
kubectl get k8srequirenonroot require-nonroot -o jsonpath='{.status.totalViolations}'
```

Gỡ:

```powershell
kubectl delete -f cloud/w10/day-a/policies/constraints/
kubectl delete -f cloud/w10/day-a/policies/templates/
```
