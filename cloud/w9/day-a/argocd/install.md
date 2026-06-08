# Cài ArgoCD lên minikube

Quick guide chạy một lần ở D1. Cần `minikube status` = Running trước.

## 1. Cài core

```powershell
kubectl create namespace argocd
kubectl apply -n argocd --server-side --force-conflicts `
  -f https://raw.githubusercontent.com/argoproj/argo-cd/stable/manifests/install.yaml

kubectl -n argocd rollout status deploy/argocd-server
kubectl -n argocd rollout status statefulset/argocd-application-controller
```

`--server-side --force-conflicts` bắt buộc vì CRD `applicationsets.argoproj.io`
vượt 262144 bytes annotation limit của client-side apply.

## 2. Lấy password admin ban đầu

```powershell
$b64 = kubectl -n argocd get secret argocd-initial-admin-secret -o jsonpath="{.data.password}"
$pwd = [Text.Encoding]::UTF8.GetString([Convert]::FromBase64String($b64))
Write-Output $pwd
```

Đổi password ngay sau lần đăng nhập đầu (User Info → Update Password).

## 3. Port-forward UI

```powershell
kubectl port-forward -n argocd svc/argocd-server 18080:443
```

Mở https://localhost:18080. Cert self-signed, browser cảnh báo, chọn Advanced
→ Proceed. Username `admin`, password ở bước 2.

Lưu ý port 8080 trên Windows có thể nằm trong excluded port range, dùng
`18080` thay vì `8080`.

## 4. (Tùy chọn) Cài argocd CLI

```powershell
choco install argocd-cli
argocd login localhost:18080 --username admin --password <password> --insecure
```

## 5. Apply Application thử nghiệm

```powershell
kubectl apply -f cloud/w9/day-a/argocd/guestbook-application.yaml
kubectl -n argocd get application
```

UI sẽ hiện app `guestbook` → tự sync → Synced + Healthy.

## 6. Demo rollback bằng `git revert`

```powershell
git log --oneline -5
git revert <sha-cua-commit-can-revert>
git push
```

ArgoCD tự sync về trạng thái Git mới (sau revert).

## 7. Clean up

Không xoá namespace `argocd` nếu còn dùng cho D2 / D3 / lab.

```powershell
kubectl delete application guestbook -n argocd
```
