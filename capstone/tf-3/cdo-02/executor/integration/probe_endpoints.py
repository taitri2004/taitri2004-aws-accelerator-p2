"""Probe 3 endpoint AI engine riêng lẻ (detect/decide/verify) — bắt lỗi schema/contract.

Chĩa vào API nào tuỳ env ENGINE_BASE_URL:
  local: ENGINE_BASE_URL=http://127.0.0.1:8540  python probe_endpoints.py
  AWS:   ENGINE_BASE_URL=http://internal-...elb.amazonaws.com  python probe_endpoints.py
         (chỉ chạy được từ trong VPC — bastion EC2 hoặc pod EKS)
"""
from __future__ import annotations
import os
import sys
import json

# cho phép import module executor (thư mục cha)
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault("ENGINE_BASE_URL", "http://127.0.0.1:8540")
os.environ.setdefault("AUTH_MODE", "mock")  # mock | sigv4 (AWS thật dùng sigv4)
os.environ.setdefault("TENANT_ID", "6c8b4b2b-4d45-4209-a1b4-4b532d56a31c")  # cdo-2 (deployment §2.C)

from engine_client import EngineClient  # noqa: E402

BASE = os.environ["ENGINE_BASE_URL"]
TW = [{
    "ts": "2026-06-25T10:00:00.123Z",
    "tenant_id": os.environ["TENANT_ID"],
    "service": "order-service",
    "signal_name": "service_error_rate",
    "value": 0.45,
    "labels": {"system": "E-COMMERCE", "namespace": "production", "deployment": "order-service"},
}]


def main() -> int:
    print(f"Probe AI engine @ {BASE} (auth={os.environ['AUTH_MODE']})\n")
    c = EngineClient()
    cases = [
        ("detect", lambda: c.detect(TW, correlation_id="corr-1",
                                    idempotency_key="idem-1", dry_run_mode=True)),
        ("decide", lambda: c.decide("corr-1",
                                    {"target_service": "order-service",
                                     "suspected_fault_type": "db", "system": "E-COMMERCE"},
                                    "idem-1", True)),
        ("verify", lambda: c.verify("corr-1",
                                    {"action": "RESTART_DEPLOYMENT",
                                     "target": "deployment/order-service",
                                     "status": "COMPLETED", "execution_time_seconds": 45},
                                    TW, idempotency_key="idem-1", dry_run_mode=True)),
    ]
    failed = 0
    for name, fn in cases:
        try:
            r = fn()
            print(f"[OK]   {name}: {json.dumps(r)[:110]}")
        except Exception as e:  # noqa: BLE001
            failed += 1
            print(f"[ERR]  {name}: {type(e).__name__}: {str(e)[:180]}")
    print(f"\n{'PASS' if failed == 0 else 'FAIL'} — {len(cases) - failed}/{len(cases)} endpoint OK")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
