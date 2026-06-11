# GitHub Actions workflow samples

Folder này lưu workflow tham khảo. Workflow validate cho W9-D1 chạy thật ở
`.github/workflows/validate-w9-day-a.yml`.

## Files

| File | Mục đích |
|---|---|
| `validate.yml` | Trigger khi PR sửa manifest app-of-apps demo → chạy `kubeconform` validate Kubernetes manifests |
| `tf-plan.yml` | Trigger khi PR mở/sửa file `cloud/w8/exercise/**` → fmt + validate + plan → comment plan vào PR |
| `tf-apply.yml` | Trigger khi merge `main` → apply qua env `prod` (cần manual approval) |

## Điều kiện cho Terraform workflow

1. **IAM role cho GitHub OIDC**:
   - Tạo OIDC provider `token.actions.githubusercontent.com` (một lần / account).
   - Tạo role `gha-tf-plan` (ReadOnly + STS) và `gha-tf-apply` (đủ quyền apply).
   - Trust policy ràng buộc `sub` với owner + repo cụ thể.
2. **GitHub Environment `prod`** ở Settings → Environments, Required reviewers
   được cấu hình.
3. **Backend state bucket** đã tồn tại
   (xem `cloud/w8/exercise/bootstrap`).
