"""Mock AI Engine — trả response đúng schema ai-api-contract.md để test executor local.

Dùng tạm cho tới khi AIO giao mock API thật (mai). Chạy: python mock_engine.py
Stdlib only (http.server) — không cần Flask.
"""
from __future__ import annotations
import json
import os
from http.server import BaseHTTPRequestHandler, HTTPServer

HOST = os.getenv("MOCK_HOST", "127.0.0.1")   # 0.0.0.0 bị chặn trên Windows (WinError 10013)
PORT = int(os.getenv("MOCK_PORT", "8080"))

# Bật để test các nhánh: normal | regression | escalate | 503 | 429
SCENARIO = os.getenv("MOCK_SCENARIO", "normal")


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *a):  # im lặng
        pass

    def _send(self, code: int, body: dict | None = None):
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        if body is not None:
            self.wfile.write(json.dumps(body).encode())

    def do_GET(self):
        if self.path in ("/health", "/ready"):
            return self._send(200, {"status": "ok"})
        self._send(404)

    def do_POST(self):
        length = int(self.headers.get("Content-Length", 0))
        _ = self.rfile.read(length)  # body (bỏ qua trong mock)

        # Inject lỗi để test fallback/backoff
        if SCENARIO == "503":
            return self._send(503, {"error": "engine unavailable"})
        if SCENARIO == "429":
            return self._send(429, {"error": "rate limited"})

        if self.path == "/v1/detect":
            return self._send(200, {
                "anomaly_detected": True,
                "severity": 0.85,
                "anomaly_context": {
                    "target_service": "emailservice",
                    "suspected_fault_type": "f3",
                    "system": "OB",
                    "trigger_metric": "service_error_rate",
                    "trigger_value": 0.42,
                },
                "confidence": 0.92,
                "reasoning": "error_rate 0.42 > ngưỡng 0.05 + OOM memory cao trên emailservice.",
                "correlation_id": "c1a2b3c4-d5e6-4f70-8h9i-0j1k2l3m4n5o",
            })

        if self.path == "/v1/decide":
            return self._send(200, {
                "matched_runbook": "RestartDeploymentRunbook",
                "pattern_type": "deferred" if SCENARIO == "deferred" else "urgent",
                "action_plan": [{
                    "step": 1,
                    "action": "RESTART_DEPLOYMENT",
                    "target": "deployment/emailservice",
                    "params": {"namespace": "onlineboutique-tnt-a",
                               "grace_period_seconds": 30},
                }],
                "blast_radius_config": {
                    "max_pod_impact_pct": 25,
                    "circuit_breaker_error_rate": 0.20,
                    "allowed_namespaces": ["onlineboutique-tnt-a", "onlineboutique-tnt-b"],
                    "forbidden_namespaces": ["kube-system", "argocd", "self-heal-system"],
                },
                "verify_policy": {
                    "window_seconds": 120,
                    "success_conditions": ["pod_ready == true", "service_error_rate < 0.05"],
                    "on_fail": "ESCALATE",
                },
                "cost_cap_exceeded": False,
            })

        if self.path == "/v1/verify":
            if SCENARIO == "regression":
                return self._send(200, {"success": False, "regression_detected": True,
                                        "next_action": "ROLLBACK"})
            if SCENARIO == "escalate":
                return self._send(200, {"success": False, "regression_detected": False,
                                        "next_action": "ESCALATE",
                                        "escalation_bundle": {"summary": "could not resolve",
                                                              "logs_ref": "s3://.../logs"}})
            return self._send(200, {"success": True, "regression_detected": False,
                                    "next_action": "DONE"})

        self._send(404)


if __name__ == "__main__":
    print(f"Mock engine on {HOST}:{PORT} (scenario={SCENARIO})")
    HTTPServer((HOST, PORT), Handler).serve_forever()
