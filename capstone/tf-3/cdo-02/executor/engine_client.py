"""Client gọi AI Engine — bám đúng schema ai-api-contract.md (3 endpoint) + xử lý error code.

Headers: X-Tenant-Id, X-Correlation-Id, Idempotency-Key, X-Dry-Run-Mode, Content-Type.
Auth (contract 25/06): AI endpoint = Local Trust in-cluster (K8s NetworkPolicy) → KHÔNG gửi
Authorization/SigV4. SigV4 chỉ còn là legacy (AUTH_MODE=sigv4). IRSA chỉ dùng cho AWS services.
Error codes (ai-api §4): 400 no-retry · 409 conflict · 429 backoff · 503 fallback.
"""
from __future__ import annotations
import time
import uuid
import logging
from typing import Any

import requests

from config import CFG

log = logging.getLogger("engine_client")


# ---- Typed exceptions theo error code (ai-api §4) ----
class EngineError(Exception): ...
class EngineBadRequest(EngineError): ...      # 400/422 - fix code, KHÔNG retry
class EngineForbidden(EngineError): ...       # 403 - tenant mismatch, KHÔNG retry → escalate
class EngineConflict(EngineError): ...        # 409 - trùng Idempotency-Key
class EngineRateLimited(EngineError): ...     # 429 - backoff
class EngineServerError(EngineError): ...     # 500 - retry 2x backoff rồi escalate
class EngineUnavailable(EngineError): ...     # 503 - upstream down → CDO BẮT BUỘC fallback


def _auth_headers() -> dict[str, str]:
    """Local Trust in-cluster (mặc định) → KHÔNG có Authorization; truy cập do NetworkPolicy chặn.
    AUTH_MODE=sigv4 (legacy) → SigV4 được ký ở _signed_request, không thêm header tại đây."""
    return {}


def _new_id() -> str:
    return str(uuid.uuid4())


class EngineClient:
    def __init__(self, base_url: str | None = None, tenant_id: str | None = None):
        self.base = (base_url or CFG.engine_base_url).rstrip("/")
        self.tenant_id = tenant_id or CFG.tenant_id

    # ---------- public API (3 endpoint) ----------
    # NOTE: AI engine (FastAPI) yêu cầu idempotency_key + correlation_id + dry_run_mode
    # nằm TRONG body cả 3 endpoint (xác nhận qua demo API AIO 25/06). Vẫn gửi kèm
    # header X-Correlation-Id / Idempotency-Key để tương thích spec cũ.
    def detect(self, telemetry_window: list[dict], correlation_id: str | None = None,
               idempotency_key: str | None = None, dry_run_mode: bool = False) -> dict:
        cid = correlation_id or _new_id()
        body = {
            "idempotency_key": idempotency_key or _new_id(),
            "correlation_id": cid,
            "dry_run_mode": dry_run_mode,
            "telemetry_window": telemetry_window,
        }
        headers = {
            "X-Correlation-Id": cid,
            "Idempotency-Key": body["idempotency_key"],
            "X-Dry-Run-Mode": str(dry_run_mode).lower(),
        }
        return self._call("POST", "/v1/detect", body, headers)

    def decide(self, correlation_id: str, anomaly_context: dict,
               idempotency_key: str, dry_run_mode: bool) -> dict:
        body = {
            "idempotency_key": idempotency_key,
            "correlation_id": correlation_id,
            "anomaly_context": anomaly_context,
            "dry_run_mode": dry_run_mode,
        }
        headers = {
            "X-Correlation-Id": correlation_id,
            "Idempotency-Key": idempotency_key,
            "X-Dry-Run-Mode": str(dry_run_mode).lower(),
        }
        return self._call("POST", "/v1/decide", body, headers)

    def verify(self, correlation_id: str, action_executed: dict,
               post_telemetry_window: list[dict],
               idempotency_key: str | None = None, dry_run_mode: bool = False) -> dict:
        body = {
            "idempotency_key": idempotency_key or _new_id(),
            "correlation_id": correlation_id,
            "dry_run_mode": dry_run_mode,
            "action_executed": action_executed,
            "post_telemetry_window": post_telemetry_window,
        }
        headers = {
            "X-Correlation-Id": correlation_id,
            "Idempotency-Key": body["idempotency_key"],
            "X-Dry-Run-Mode": str(dry_run_mode).lower(),
        }
        return self._call("POST", "/v1/verify", body, headers)

    # ---------- transport + error handling ----------
    def _call(self, method: str, path: str, body: dict, extra_headers: dict) -> dict:
        url = self.base + path
        headers = {
            "Content-Type": "application/json",
            "X-Tenant-Id": self.tenant_id,
            **_auth_headers(),
            **extra_headers,
        }
        attempt = 0
        while True:
            attempt += 1
            try:
                resp = self._signed_request(method, url, body, headers)
            except requests.exceptions.RequestException as e:
                # Engine không kết nối được/timeout → coi như unavailable → CDO fallback
                raise EngineUnavailable(f"{path}: {e}") from e
            code = resp.status_code

            if 200 <= code < 300:
                return resp.json()
            if code in (400, 422):  # 422 = FastAPI schema validation → fix code, KHÔNG retry
                raise EngineBadRequest(f"{path} [{code}]: {resp.text}")
            if code == 403:         # tenant mismatch (X-Tenant-Id ≠ payload) → KHÔNG retry
                raise EngineForbidden(f"{path}: forbidden (tenant mismatch): {resp.text}")
            if code == 409:
                raise EngineConflict(f"{path}: idempotency conflict")
            if code == 429:
                if attempt > CFG.max_retries_429:
                    raise EngineRateLimited(f"{path}: rate-limited after {attempt} tries")
                wait = CFG.backoff_base_s * (2 ** (attempt - 1))  # exponential backoff
                log.warning("429 on %s, backoff %.1fs (try %d)", path, wait, attempt)
                time.sleep(wait)
                continue
            if code == 500:         # lỗi nội bộ → retry tối đa max_retries_500 (backoff 1s,3s)
                if attempt > CFG.max_retries_500:
                    raise EngineServerError(f"{path}: 500 after {attempt} tries: {resp.text}")
                wait = CFG.backoff_500_s[min(attempt - 1, len(CFG.backoff_500_s) - 1)]
                log.warning("500 on %s, backoff %.1fs (try %d)", path, wait, attempt)
                time.sleep(wait)
                continue
            if code == 503:         # upstream (Bedrock/DDB/S3) down → fallback
                raise EngineUnavailable(f"{path}: engine/upstream unavailable")
            resp.raise_for_status()

    def _signed_request(self, method: str, url: str, body: dict, headers: dict):
        if CFG.auth_mode == "sigv4":
            return self._sigv4_request(method, url, body, headers)
        return requests.request(method, url, json=body, headers=headers,
                                timeout=CFG.request_timeout_s)

    def _sigv4_request(self, method: str, url: str, body: dict, headers: dict):
        """Ký SigV4 bằng botocore (chỉ dùng khi chạy thật trên AWS)."""
        import json
        from botocore.auth import SigV4Auth
        from botocore.awsrequest import AWSRequest
        from botocore.session import Session

        data = json.dumps(body)
        aws_req = AWSRequest(method=method, url=url, data=data, headers=headers)
        creds = Session().get_credentials()
        SigV4Auth(creds, "execute-api", CFG.aws_region).add_auth(aws_req)
        return requests.request(method, url, data=data,
                                headers=dict(aws_req.headers), timeout=CFG.request_timeout_s)
