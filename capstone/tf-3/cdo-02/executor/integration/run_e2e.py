"""Chạy TRỌN VÒNG self-heal (detect -> decide -> safety -> execute -> verify) đập API thật.

EXECUTE_MODE=mock => execute giả (không cần cluster), chỉ test đường tích hợp engine.
  local: ENGINE_BASE_URL=http://127.0.0.1:8540  python run_e2e.py
  AWS:   ENGINE_BASE_URL=<internal-alb-dns>  AUTH_MODE=sigv4  python run_e2e.py  (chạy trong VPC)
"""
from __future__ import annotations
import os
import sys
import json

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault("ENGINE_BASE_URL", "http://127.0.0.1:8540")
os.environ.setdefault("AUTH_MODE", "mock")
os.environ.setdefault("EXECUTE_MODE", "mock")
os.environ.setdefault("DRY_RUN", "false")
os.environ.setdefault("TENANT_ID", "6c8b4b2b-4d45-4209-a1b4-4b532d56a31c")  # cdo-2 (deployment §2.C)

from orchestrator import run_remediation  # noqa: E402

ALERT = {
    "telemetry_window": [{
        "ts": "2026-06-25T10:00:00.123Z",
        "tenant_id": os.environ["TENANT_ID"],
        "service": "order-service",
        "signal_name": "service_error_rate",
        "value": 0.45,
        "labels": {"system": "E-COMMERCE", "namespace": "onlineboutique", "deployment": "adservice"},
    }],
    "post_telemetry_window": [{
        "ts": "2026-06-25T10:05:00.000Z",
        "signal_name": "service_error_rate", "value": 0.0,
        "labels": {"namespace": "onlineboutique", "deployment": "adservice"},
    }],
}


def main() -> int:
    print(f"E2E @ {os.environ['ENGINE_BASE_URL']} (execute={os.environ['EXECUTE_MODE']})\n")
    out = run_remediation(ALERT)
    print("\n=== FINAL OUTCOME ===", json.dumps(out))
    return 0 if out.get("outcome") in ("RESOLVED", "DRY_RUN") else 1


if __name__ == "__main__":
    raise SystemExit(main())
