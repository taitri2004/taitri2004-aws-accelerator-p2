# Cost Analysis - Task Force 3 · CDO-02

<!-- Doc owner: Nhóm CDO-02
     Status: Skeleton (W11 T6 Pack #1) → Measured actual (W12 T4 Pack #2)
     Word target: 800-1500 từ
     LƯU Ý: số dưới đây là FORECAST/ƯỚC TÍNH. Measured actual fill ở §5 trong W12.
     §4 so sánh dùng approach kiến trúc GENERIC (không so nhóm CDO khác - chỉ đạo mentor). -->

> Angle K8s-heavy → phần lớn cost là **shared fixed** (cluster, NAT, endpoints, executor pod); marginal per-tenant thấp. Số forecast us-east-1, validate bằng measured actual W12.

## 1. Cost model per tenant (forecast)

Giả định: workload nhỏ (Online Boutique ~11 service), ~1000 self-heal cycle/tháng/tenant, audit ~vài trăm MB/tháng.

| Component | Unit cost | Tenant avg usage | $/tenant/month |
|---|---|---|---|
| Compute share (EKS node + executor pod) | ~$60/mo / N tenant | 1 namespace | ~$6 (10 tenant) |
| Executor pod (in-cluster) | trong node cost | always-on, nhỏ | ~$0 marginal |
| DynamoDB (idempotency) | on-demand | ~vài K write | ~$0.10 |
| S3 Object Lock (audit) | $0.023/GB-mo | ~0.5 GB | ~$0.05 |
| Athena query | $5/TB scan | nhẹ | ~$0.10 |
| AI inference (Bedrock)* | ~$0.003-0.01/call | ~1000 call | ~$3-8 |
| Observability (Prometheus/Grafana) | nhẹ | — | ~$0.50 |
| **Marginal / tenant / month** | | | **~$10-15** |

*AI inference do engine (AI team) chịu; đưa vào model để có cost-per-correct-decision (§5.3).

**Shared fixed cost (không scale theo tenant)**:

| Item | $/month |
|---|---|
| EKS control plane | ~$73 |
| NAT Gateway | ~$33 |
| VPC interface endpoints (×~3) | ~$22 (S3/DynamoDB gateway endpoint free) |
| 2× node t3.medium (spot) | ~$17-60 tuỳ spot/on-demand |
| Secrets Manager (~3 secret) | ~$1.2 |
| **Tổng fixed** | **~$150-190** |

## 2. Cost at scale

| Tenant count | Fixed + marginal | Avg per-tenant |
|---|---|---|
| 2 (sandbox) | ~$170 + 2×$12 = ~$194 | ~$97 |
| 10 | ~$190 + 10×$12 = ~$310 | ~$31 |
| 50 | ~$300 + 50×$12 = ~$900 | ~$18 |
| 200 | ~$600 + 200×$12 = ~$3000 | ~$15 |

*Per-tenant giảm mạnh do fixed cost (cluster/NAT/endpoint/executor) amortize — marginal cost gần như chỉ là inference + storage.*

## 3. Cost optimization applied

- ☑ **Spot instances** cho EKS node (non-critical sandbox, ~70% saving).
- ☑ **Executor right-sizing** (1 pod nhỏ, HPA min 1) → không over-provision.
- ☑ **S3 lifecycle**: audit Standard → Glacier sau 90d hot (Object Lock vẫn giữ).
- ☑ **DynamoDB on-demand** (write thưa, không cần provisioned).
- ☑ **VPC gateway endpoint** (S3/DynamoDB free) thay vì interface endpoint chỗ có thể.
- ☐ **Bedrock prompt caching** (AI team) — giảm inference cost.
- ☐ **Single NAT** (1 AZ) cho sandbox thay vì NAT mỗi AZ — chấp nhận giảm HA để tiết kiệm.

## 4. Cost vs alternative architecture (generic)

| Approach | $/tenant/mo (10 tenant) | Why diff |
|---|---|---|
| **K8s-heavy in-cluster (chọn)** | ~$31 | 1 executor pod nhỏ always-on; thực thi in-cluster, no kubeconfig egress |
| Serverless (Step Functions+Lambda) | tương đương/thấp hơn idle | scale-to-zero nhưng cần kubeconfig ngoài + xa workload |
| Managed-services heavy | cao hơn | nhiều managed service, xa K8s workload |

## 5. Measured actual (Pack #2 — fill W12)

### 5.1 2-week capstone spend

| Service | Forecast | Actual | Delta |
|---|---|---|---|
| EKS + node (gồm executor pod) | $X | — | — |
| NAT + endpoints | $X | — | — |
| DynamoDB + S3 + Athena | $X | — | — |
| AI inference (joint) | $X | — | — |
| **Total** | $X | — | — |

### 5.2 Per-tenant actual (sau onboard ≥2 tenant test)

| Tenant test | Load | $/day | Extrapolate $/mo |
|---|---|---|---|
| tnt-a | small | — | — |
| tnt-b | medium | — | — |

### 5.3 Cost-per-correct-decision (joint AI eval)

| Metric | Value |
|---|---|
| Total self-heal cycle | — |
| Correct (auto-resolved) | — |
| Total AI cost | — |
| **Cost / correct decision** | — |

## 6. Cost guardrails

- Budget alert 70% / 90% / 100% (AWS Budgets).
- Per-tenant rate limit (API GW usage plan) chống runaway.
- Bedrock daily spend cap (CloudWatch alarm) — phối hợp AI.
- Auto-teardown sandbox sau code freeze để không tốn tiền thừa.

## 7. Cost recommendations for production

- Savings Plan / Reserved cho EKS node sau 3 tháng baseline.
- Multi-AZ NAT chỉ bật cho production (sandbox 1 NAT đủ).
- S3 tiering + audit retention policy theo compliance thật.

## Related documents

- [`02_infra_design.md`](02_infra_design.md) - component drive cost ở §1
- [`04_deployment_design.md`](04_deployment_design.md) - deploy strategy ảnh hưởng cost
- [`07_test_eval_report.md`](07_test_eval_report.md) - load test validate giả định cost (Pack #2)
- [`08_adrs.md`](08_adrs.md) - ADR-001 (K8s-heavy angle)
