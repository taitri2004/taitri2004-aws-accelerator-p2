# W9 — Day A: GitOps & CI/CD

Scope D1: GitHub Actions plan-on-PR / apply-on-merge, ArgoCD vs Flux,
App-of-Apps, sync waves, rollback (`git revert` vs `kubectl rollout undo`).
Tài liệu nền: [`knowledge/w9-foundation-gitops-observability-canary.md`](../../../knowledge/w9-foundation-gitops-observability-canary.md) §1–§4.

## Layout

```
day-a/
  README.md
  notes.md                    Ghi chú self-study
  EVIDENCE_PACK.md            Tổng hợp bằng chứng (screenshot + log)
  screenshots/                Ảnh chụp UI / terminal
  argocd/
    install.md                Quick guide cài ArgoCD lên minikube
    guestbook-application.yaml
    nginx-demo-application.yaml
    root-app-of-apps.yaml     Mẫu App-of-Apps cho lab
    manifests/
      nginx-demo/             Manifests dùng cho demo git revert
  .github-workflows/          Mẫu workflow (đổi tên `.github-workflows`
                              để GitHub không tự trigger; copy sang
                              `.github/workflows/` khi muốn enable thật)
```

## Nội dung

1. Cài ArgoCD core lên minikube W8, port-forward UI.
2. Apply `Application` mẫu (guestbook) để minh hoạ ArgoCD pull từ Git.
3. Demo selfHeal: scale tay → ArgoCD revert.
4. Demo `git revert` rollback: thay đổi manifest qua Git → ArgoCD sync → revert.
5. Workflow Terraform plan-on-PR / apply-on-merge với GitHub OIDC.

Chi tiết bằng chứng xem `EVIDENCE_PACK.md`.
