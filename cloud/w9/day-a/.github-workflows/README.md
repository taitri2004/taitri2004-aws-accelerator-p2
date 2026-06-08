# GitHub Actions workflow mẫu — W9 D1

> ⚠️ Folder này tên `.github-workflows` (dấu `-`), KHÔNG phải `.github/workflows`,
> để GitHub **không** trigger tự động khi push. Đây là material học/đọc.
>
> Khi muốn chạy thật: copy file `.yml` sang `.github/workflows/` ở root repo
> và thiết lập IAM role + GitHub Environment trước.

## File trong folder

| File | Mục đích |
|---|---|
| `tf-plan.yml` | Trigger khi PR mở/sửa file `cloud/w8/exercise/**` → fmt + validate + plan → comment plan vào PR |
| `tf-apply.yml` | Trigger khi merge `main` → apply qua env `prod` (cần manual approval) |

## Trước khi enable thật, cần:

1. **IAM role cho GitHub OIDC** (account 749043157095):
   - Tạo OIDC provider `token.actions.githubusercontent.com` (1 lần / account).
   - Tạo role `gha-tf-plan` (ReadOnly + STS) và `gha-tf-apply` (đủ quyền terraform apply).
   - Trust policy ràng buộc `sub` = `repo:taitri2004/taitri2004-aws-accelerator-p2:*`.
2. **GitHub Environment `prod`** ở Settings → Environments → Required reviewers = chính HV.
3. **Backend state bucket** đã tồn tại (W8 đã làm trong `cloud/w8/exercise/bootstrap`).

## Demo D1 (không cần chạy thật)

Đủ để hiểu pattern → viết vào `notes.md` § GH Actions + screenshot phần code.
Apply thật để dành sau khi có IAM role.
