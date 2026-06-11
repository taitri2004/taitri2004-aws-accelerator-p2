# W9 — Day A: GitOps & CI/CD

Scope D1: GitOps với ArgoCD, Application, self-heal, rollback bằng Git,
App-of-Apps, sync waves và CI validate manifest trên pull request.
Tài liệu nền: [`knowledge/w9-foundation-gitops-observability-canary.md`](../../../knowledge/w9-foundation-gitops-observability-canary.md) §1–§4.

## Layout

```
day-a/
  README.md
  EVIDENCE_PACK.md            Tổng hợp bằng chứng (screenshot + log)
  screenshots/                Ảnh chụp UI / terminal
  argocd/
    install.md                Quick guide cài ArgoCD lên minikube
    guestbook-application.yaml
    nginx-demo-application.yaml
    root-app-of-apps.yaml     Root Application cho app-of-apps
    app-of-apps-demo/
      root.yaml               Root Application
      apps/                   Application con
      manifests/waves-demo/   Namespace, ConfigMap, Deployment, Service
    manifests/
      nginx-demo/             Manifests dùng cho demo git revert
  .github-workflows/          Workflow samples
```

Workflow chạy thật nằm ở repo root: `.github/workflows/validate-w9-day-a.yml`.

## Lab 0-7

| Lab | Nội dung | Artifact chính |
|---|---|---|
| 0 | Chuẩn bị cluster, repo và app manifest trên Git | `argocd/manifests/nginx-demo/` |
| 1 | Cài ArgoCD | `argocd/install.md` |
| 2 | Tạo Application để ArgoCD tự sync | `argocd/guestbook-application.yaml`, `argocd/nginx-demo-application.yaml` |
| 3 | Sync qua Git và self-heal khi có drift | `guestbook-application.yaml` có `selfHeal: true` |
| 4 | Rollback bằng `git revert` | `argocd/manifests/nginx-demo/deployment.yaml` + git history |
| 5 | App-of-Apps | `argocd/root-app-of-apps.yaml`, `argocd/app-of-apps-demo/apps/waves-demo.yaml` |
| 6 | Sync waves | `argocd/app-of-apps-demo/manifests/waves-demo/` |
| 7 | CI validate manifest trên PR | `.github/workflows/validate-w9-day-a.yml` |

## Run

```powershell
kubectl apply -f cloud/w9/day-a/argocd/guestbook-application.yaml
kubectl apply -f cloud/w9/day-a/argocd/nginx-demo-application.yaml
kubectl apply -f cloud/w9/day-a/argocd/root-app-of-apps.yaml
```

Chi tiết bằng chứng xem `EVIDENCE_PACK.md`.
