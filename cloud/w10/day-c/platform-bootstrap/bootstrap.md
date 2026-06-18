# Bootstrap mini platform end-to-end (< 2h từ repo)

Mục tiêu W10: từ fresh cluster dựng lại toàn bộ stack W8→W10. ArgoCD biến phần
lớn việc thành "apply root app rồi chờ reconcile".

## Thứ tự (mỗi lớp là tiền đề lớp sau)

```powershell
# 0. Cluster (W8 IaC hoặc minikube cho lab)
minikube start --cpus=2 --memory=4000 --driver=docker

# 1. GitOps controller (W9) — sau bước này mọi thứ kéo từ Git
kubectl create ns argocd
kubectl apply -n argocd --server-side --force-conflicts `
  -f https://raw.githubusercontent.com/argoproj/argo-cd/stable/manifests/install.yaml
kubectl -n argocd rollout status deploy/argocd-server

# 2. App-of-apps kéo observability + canary + app (W9)
kubectl apply -f cloud/w9/lab/argocd/root.yaml

# 3. Security layer (W10)
#    D1: RBAC + Gatekeeper
kubectl apply -f cloud/w10/day-a/rbac/
kubectl apply -f cloud/w10/day-a/policies/templates/ ; Start-Sleep 10
kubectl apply -f cloud/w10/day-a/policies/constraints/
#    D2: ESO + verify signature
kubectl apply -f cloud/w10/day-b/eso/secretstore-fake.yaml
kubectl apply -f cloud/w10/day-b/eso/externalsecret-fake.yaml
kubectl apply -f cloud/w10/day-b/signing/verify-keyless.yaml

# 4. Guardrail tài nguyên (D3)
kubectl apply -f cloud/w10/day-c/platform-bootstrap/00-namespace.yaml
kubectl apply -f cloud/w10/day-c/platform-bootstrap/resourcequota.yaml
kubectl apply -f cloud/w10/day-c/platform-bootstrap/limitrange.yaml

# 5. Smoke test
kubectl get applications -n argocd          # tất cả Synced/Healthy
kubectl get constraints                     # 4 constraint active
kubectl -n platform-app get resourcequota   # quota áp dụng
```

## Checklist nghiệm thu (acceptance W10)

- [ ] RBAC 3 role `developer`/`sre`/`viewer` (D1)
- [ ] 4 Gatekeeper constraint enforce (D1)
- [ ] ESO rotate secret < 60s no-restart (D2)
- [ ] Admission reject unsigned image (D2)
- [ ] ResourceQuota + LimitRange áp dụng (D3)
- [ ] ArgoCD Synced/Healthy + canary auto-abort (W9)
- [ ] Toàn bộ dựng lại < 2h từ repo

Phần lớn thời gian là chờ image pull + reconcile, không phải thao tác tay.
