"""Kiểm tra executor map đúng error code engine (ai-api §4): 422/400 -> EngineBadRequest.

Gửi body cố tình thiếu field -> server FastAPI trả 422 -> client PHẢI raise EngineBadRequest
(không phải HTTPError thô) để orchestrator xử lý gọn thay vì crash.
"""
from __future__ import annotations
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault("ENGINE_BASE_URL", "http://127.0.0.1:8540")
os.environ.setdefault("AUTH_MODE", "mock")
os.environ.setdefault("TENANT_ID", "6c8b4b2b-4d45-4209-a1b4-4b532d56a31c")  # cdo-2 (deployment §2.C)

from engine_client import EngineClient, EngineBadRequest  # noqa: E402


def main() -> int:
    c = EngineClient()
    try:
        c._call("POST", "/v1/detect", {"telemetry_window": []}, {})  # thiếu 3 field bắt buộc
        print("[FAIL] không có exception (server không validate?)")
        return 1
    except EngineBadRequest as e:
        print(f"[OK] 422 -> EngineBadRequest: {str(e)[:80]}")
        return 0
    except Exception as e:  # noqa: BLE001
        print(f"[FAIL] sai loại exception: {type(e).__name__}: {str(e)[:80]}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
