# Infra (Terraform) — CDO-02 Self-Heal Platform

Base infra cho Pack #1 (EOD T6 W11): **VPC + EKS 1.31 + state/audit chạy được**. Khớp [`../docs/02_infra_design.md`](../docs/02_infra_design.md) + [`../docs/04_deployment_design.md`](../docs/04_deployment_design.md).

## Layout

```
infra/
├── modules/
│   ├── networking/        # VPC + subnet + NAT (single) + VPC endpoints + SG
│   ├── eks/               # EKS 1.31 + managed node group (spot) + IRSA + secrets KMS
│   ├── state-audit/       # S3 Object Lock (Compliance 90d) + DynamoDB idempotency + KMS
│   └── tenant-provision/  # [stage-2] namespace + RBAC + NetworkPolicy per tenant
└── environments/
    └── sandbox/           # root wiring base infra (networking + eks + state-audit)
```

## Thứ tự apply

**Bootstrap state backend (1 lần)** — dùng local state trước, hoặc S3 remote state với **S3 native lockfile** (Terraform ≥1.10 → không cần DynamoDB lock):
```bash
cd environments/sandbox
# Lần đầu chạy local state (backend đang comment):
terraform init
terraform apply
```
Khi muốn remote state: tạo S3 bucket thủ công rồi mở khối backend (`use_lockfile = true`) trong versions.tf, chạy `terraform init -migrate-state`.

**Stage 1 — base infra (T6):**
```bash
terraform apply   # tạo VPC + EKS 1.31 + S3 Object Lock + DynamoDB
aws eks update-kubeconfig --name tf-3-cdo2-sandbox --region us-east-1
kubectl get nodes   # verify cluster live
```

**Stage 2 — tenant provisioning (sau khi cluster up):** xem cuối `environments/sandbox/main.tf` (khối tenant-provision đang comment + hướng dẫn). Tách stage vì kubernetes provider cần cluster đã tồn tại.

## ⚠️ Lưu ý
- **Cost**: EKS control plane + NAT + node spot ~ vài $/ngày. **Teardown sau code freeze**: `terraform destroy`.
- Region us-east-1, EKS **1.31** (khớp Client n-1).
- `single_nat_gateway = true` để tiết kiệm (ADR cost) — giảm HA, chấp nhận cho sandbox.
- Cần AWS creds + Terraform ≥1.5 + kubectl.
