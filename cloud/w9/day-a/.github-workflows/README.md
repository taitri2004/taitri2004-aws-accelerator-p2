# GitHub Actions workflow mẫu — Terraform CI

Folder này tên `.github-workflows` (gạch ngang) để GitHub không trigger tự động
khi push. Đây là material học. Khi muốn enable thật, copy file `.yml` sang
`.github/workflows/` ở root repo và thiết lập IAM role + GitHub Environment
trước.

## Files

| File | Mục đích |
|---|---|
| `tf-plan.yml` | Trigger khi PR mở/sửa file `cloud/w8/exercise/**` → fmt + validate + plan → comment plan vào PR |
| `tf-apply.yml` | Trigger khi merge `main` → apply qua env `prod` (cần manual approval) |

## Điều kiện cần trước khi enable

1. **IAM role cho GitHub OIDC**:
   - Tạo OIDC provider `token.actions.githubusercontent.com` (một lần / account).
   - Tạo role `gha-tf-plan` (ReadOnly + STS) và `gha-tf-apply` (đủ quyền apply).
   - Trust policy ràng buộc `sub` với owner + repo cụ thể.
2. **GitHub Environment `prod`** ở Settings → Environments, Required reviewers
   được cấu hình.
3. **Backend state bucket** đã tồn tại
   (xem `cloud/w8/exercise/bootstrap`).
