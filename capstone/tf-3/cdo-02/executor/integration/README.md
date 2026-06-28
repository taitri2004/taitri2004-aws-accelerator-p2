# Integration test — executor ↔ AI engine

Test code executor đập vào **API thật của AI engine** (AIO). Cùng 1 bộ script cho local & AWS — chỉ đổi `ENGINE_BASE_URL`.

## Script

| Script | Việc |
|---|---|
| `probe_endpoints.py` | Gọi 3 endpoint riêng lẻ (detect/decide/verify) — kiểm tra khớp schema/contract |
| `run_e2e.py` | Chạy trọn vòng `run_remediation()` (detect→decide→safety→execute→verify) |
| `probe_errors.py` | Kiểm tra map error code: 422/400 → `EngineBadRequest` (không crash) |

## Cấu hình qua env

| Env | Default | Ý nghĩa |
|---|---|---|
| `ENGINE_BASE_URL` | `http://127.0.0.1:8540` | URL AI engine |
| `AUTH_MODE` | `mock` | `mock` (local) / `sigv4` (AWS thật, ký IAM) |
| `EXECUTE_MODE` | `mock` | `mock` (execute giả) / `live` (kubectl, cần cluster) |
| `TENANT_ID` | UUID demo | header `X-Tenant-Id` |

## A. Test LOCAL (miễn phí, không cần AWS)

```bash
# 1. Dựng dummy API của AIO (repo feat/demo) ở 1 terminal khác:
#    cd <aio>/demo/app && uvicorn main:app --host 127.0.0.1 --port 8540
# 2. Chạy test:
cd executor/integration
python probe_endpoints.py
python run_e2e.py
python probe_errors.py
```

## B. Test trên AWS (internal ALB)

ALB của AI engine là **internal** → laptop KHÔNG gọi được. Phải chạy từ **trong VPC**:
bastion EC2 cùng VPC, hoặc (W12) chính pod executor trong EKS.

```bash
export ENGINE_BASE_URL=http://internal-tf-3-ai-engine-alb-xxx.us-east-1.elb.amazonaws.com
export AUTH_MODE=sigv4          # nếu engine yêu cầu ký IAM SigV4
python run_e2e.py              # cùng script, chỉ khác URL
```

> Tóm: script không "thuộc về" local hay AWS — chỉ đổi `ENGINE_BASE_URL` và chỗ đứng của người gọi.
