# W9 — Day A (T2 08/06): GitOps & CI/CD

> Self-study D1. Scope: GitHub Actions plan-on-PR/apply-on-merge, ArgoCD vs Flux,
> App-of-Apps, sync waves, rollback (`git revert` vs `kubectl rollout undo`).
> Tài liệu nền: [`knowledge/w9-foundation-gitops-observability-canary.md`](../../../knowledge/w9-foundation-gitops-observability-canary.md) §1–§4.

## Layout

```
day-a/
├── README.md             # file này — lệnh + sơ đồ + giải thích
├── notes.md              # ghi chú tự viết khi học (commit)
├── NOTES.md              # PRIVATE — gitignore
├── screenshots/          # evidence (ArgoCD UI, GH Actions run)
├── argocd/               # Application YAML thử nghiệm
└── .github-workflows/    # workflow mẫu (tên thư mục tránh GH chạy thật)
```

## TODO hôm nay
- [ ] Đọc lý thuyết §1–§4 trong foundation note
- [ ] Cài ArgoCD lên minikube, port-forward UI, đổi password
- [ ] Tạo 1 `Application` đơn giản (guestbook hoặc nginx) → sync
- [ ] Viết workflow `tf-plan.yml` mẫu cho `cloud/w8/exercise`
- [ ] Demo rollback: `git revert` 1 commit → ArgoCD tự sync lại
- [ ] Screenshot evidence
- [ ] Commit `[W9-D1] <topic>`
