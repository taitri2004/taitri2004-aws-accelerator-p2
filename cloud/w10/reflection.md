# W10 Reflection — Secure & Operate (RBAC + Secrets + Platform)

Mục tiêu W10: cluster W8→W9 thêm hardening ở **cluster level** — RBAC 3 role,
admission policy chặn workload không an toàn, secrets rotation, reject unsigned
image. Kết thúc = mini platform end-to-end sẵn cho capstone W11–W12.

## Đã làm

- D1: RBAC (`viewer`/`developer`/`sre` + `auth can-i`) + OPA/Gatekeeper (4
  constraint, ConstraintTemplate vs Constraint) + VAP native + audit vs enforce.
- D2: Secrets Rotation (ESO + AWS Secrets Manager, rotation no-restart) + Supply
  Chain (Trivy CI + Cosign sign + verify signature ở admission + exception CVE).
- D3: Platform Integration (bootstrap W8→W10 < 2h) + ResourceQuota/LimitRange +
  chaos test + runbook/postmortem + AWS Cost Anomaly Detection.
- Lab onsite: 6-risk cluster cleanup + cluster-level enforcement *(T5–T6)*.

## Khó nhất

(điền cuối tuần)

## Bài học mới so với W9

(điền cuối tuần)

## Để dành cho capstone W11–W12

(điền cuối tuần)
