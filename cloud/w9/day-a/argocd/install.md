# ArgoCD install lên minikube — quick guide

> Chạy 1 lần ở D1. PowerShell. Đảm bảo `minikube status` = Running trước.

## 1. Cài core

```powershell
# namespace + install (stable manifest)
kubectl create namespace argocd
kubectl apply -n argocd -f https://raw.githubusercontent.com/argoproj/argo-cd/stable/manifests/install.yaml

# đợi controller ready (~1-2 phút)
kubectl -n argocd rollout status deploy/argocd-server
kubectl -n argocd rollout status statefulset/argocd-application-controller
```

## 2. Lấy password admin ban đầu

```powershell
$b64 = kubectl -n argocd get secret argocd-initial-admin-secret -o jsonpath="{.data.password}"
$pwd = [Text.Encoding]::UTF8.GetString([Convert]::FromBase64String($b64))
Write-Output "admin password: $pwd"
```

→ ghi vào `NOTES.md` (PRIVATE), KHÔNG vào notes.md.

## 3. Port-forward UI

```powershell
# chạy ở terminal riêng (giữ chạy)
kubectl port-forward -n argocd svc/argocd-server 8080:443
```

Mở https://localhost:8080 — username `admin`, password ở bước 2.
(Browser cảnh báo cert self-signed → Advanced → Proceed.)

## 4. (Tùy) Cài argocd CLI

```powershell
# nếu chưa có
choco install argocd-cli   # hoặc tải binary từ GitHub release
argocd login localhost:8080 --username admin --password $pwd --insecure
```

## 5. Apply Application thử nghiệm

```powershell
kubectl apply -f cloud/w9/day-a/argocd/guestbook-application.yaml
kubectl -n argocd get application
# trên UI sẽ thấy app "guestbook" → tự sync → Healthy + Synced
```

## 6. Demo rollback bằng git revert

```powershell
# Giả lập: sửa replicas trong manifest, commit, ArgoCD sync
# Sau đó:
git log --oneline -5
git revert <sha-cua-commit-vua-roi>
git push
# → ArgoCD tự sync → cluster về trạng thái cũ → screenshot UI
```

## 7. Clean up (nếu muốn)

```powershell
# KHÔNG xoá namespace argocd nếu còn dùng cho D2/D3/lab
kubectl delete application guestbook -n argocd
```
