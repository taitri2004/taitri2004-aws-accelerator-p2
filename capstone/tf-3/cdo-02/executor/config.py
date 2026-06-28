"""Cấu hình executor — đọc từ env, có default cho local dev."""
from __future__ import annotations
import os
from dataclasses import dataclass


@dataclass(frozen=True)
class Config:
    engine_base_url: str = os.getenv("ENGINE_BASE_URL", "http://localhost:8080")
    tenant_id: str = os.getenv("TENANT_ID", "6c8b4b2b-4d45-4209-a1b4-4b532d56a31c")  # cdo-2 UUID, X-Tenant-Id (deployment §2.C; cdo-1=d3b07384-...)
    # AI endpoint = Local Trust in-cluster (K8s NetworkPolicy) theo contract 25/06 — KHÔNG SigV4.
    # "sigv4" giữ lại làm legacy (nếu engine sau này đứng sau AWS API Gateway/ALB IAM).
    auth_mode: str = os.getenv("AUTH_MODE", "local_trust")    # local_trust | sigv4(legacy)
    aws_region: str = os.getenv("AWS_REGION", "us-east-1")

    # Execution mode
    execute_mode: str = os.getenv("EXECUTE_MODE", "mock")     # mock | live (kubectl)
    dry_run: bool = os.getenv("DRY_RUN", "false").lower() == "true"

    # Safety gate CDO tự enforce (không phụ thuộc engine) — engine spec §5.4 + §6
    confidence_min: float = float(os.getenv("CONFIDENCE_MIN", "0.6"))   # confidence < ngưỡng → escalate
    max_telemetry_tokens: int = int(os.getenv("MAX_TELEMETRY_TOKENS", "4000"))  # giới hạn payload gửi AI

    # Retry / SLA (ai-api §4)
    max_retries_429: int = 4
    backoff_base_s: float = 1.0                               # 1→2→4→8s
    max_retries_500: int = 2                                  # 500 → retry tối đa 2 lần (ai-api §4)
    backoff_500_s: tuple = (1.0, 3.0)                         # backoff 1s, 3s rồi escalate
    request_timeout_s: float = 5.0

    # Circuit breaker
    cb_window: int = 10                                       # số cycle gần nhất
    cb_error_threshold: float = 0.5                           # >50% fail → open

    # Verify window (Client: ~5p ổn định, configurable per pattern)
    verify_window_seconds: int = int(os.getenv("VERIFY_WINDOW_S", "300"))

    # Audit
    audit_sink: str = os.getenv("AUDIT_SINK", "stdout")       # stdout | file | s3
    audit_bucket: str = os.getenv("AUDIT_BUCKET", "tf-3-aiops-audit-trail")
    idempotency_table: str = os.getenv("IDEMPOTENCY_TABLE", "tf-3-aiops-idempotency-lock")
    idempotency_mode: str = os.getenv("IDEMPOTENCY_MODE", "memory")  # memory | dynamodb

    slack_webhook: str = os.getenv("SLACK_WEBHOOK_URL", "")


CFG = Config()
