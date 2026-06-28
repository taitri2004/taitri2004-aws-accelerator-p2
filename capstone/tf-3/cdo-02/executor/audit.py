"""Audit tamper-evident (ADR-004). dev = stdout/file; prod = S3 Object Lock + prefix per-tenant."""
from __future__ import annotations
import json
import time
import logging

from config import CFG

log = logging.getLogger("audit")


class AuditLogger:
    def __init__(self, tenant_id: str, correlation_id: str):
        self.tenant_id = tenant_id
        self.correlation_id = correlation_id

    def write(self, stage: str, payload: dict) -> None:
        record = {
            **payload,                      # payload trước để KHÔNG ghi đè field canonical bên dưới
            "ts": time.strftime("%Y-%m-%dT%H:%M:%S.000Z", time.gmtime()),
            "tenant_id": self.tenant_id,
            "correlation_id": self.correlation_id,
            "stage": stage,                 # detect|decide|guardrail|execute|verify|escalate|rollback
        }
        line = json.dumps(record, ensure_ascii=False)
        if CFG.audit_sink == "s3":
            self._to_s3(record)
        elif CFG.audit_sink == "file":
            with open("audit.jsonl", "a", encoding="utf-8") as f:
                f.write(line + "\n")
        else:
            try:
                print("[AUDIT]", line)
            except UnicodeEncodeError:
                # console không phải UTF-8 (vd cp1252 trên Windows) + payload có ký tự non-ASCII
                # (vd reasoning tiếng Việt từ engine) → fallback escape ASCII, không crash
                print("[AUDIT]", json.dumps(record, ensure_ascii=True))

    def _to_s3(self, record: dict) -> None:
        import boto3
        s3 = boto3.client("s3", region_name=CFG.aws_region)
        # prefix per-tenant để isolation (03_security_design §5.2)
        key = f"audit/{self.tenant_id}/{self.correlation_id}/{record['stage']}-{int(time.time()*1000)}.json"
        s3.put_object(Bucket=CFG.audit_bucket, Key=key,
                      Body=json.dumps(record).encode(),
                      ContentType="application/json")
