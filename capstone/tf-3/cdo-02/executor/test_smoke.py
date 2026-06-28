"""Smoke test executor chống lại mock engine (in-process, không cần network).

Chạy: pytest -q
Test 4 nhánh: resolved · regression→rollback · escalate · 503 fallback.
"""
from __future__ import annotations
import importlib

import pytest

import guardrails
from engine_client import EngineClient
import orchestrator


SAMPLE = {
    "telemetry_window": [
        {"ts": "2026-06-25T10:00:00.123Z", "signal_name": "service_error_rate",
         "value": 0.42, "labels": {"service": "emailservice", "namespace": "onlineboutique-tnt-a"}},
    ],
    "post_telemetry_window": [
        {"ts": "2026-06-25T10:05:00Z", "signal_name": "service_error_rate",
         "value": 0.0, "labels": {"service": "emailservice"}},
    ],
}


class FakeEngine(EngineClient):
    """Giả lập engine theo scenario, không cần HTTP."""
    def __init__(self, scenario="normal"):
        self.scenario = scenario
        self.tenant_id = "cdo-2"

    def detect(self, telemetry_window, correlation_id=None,
               idempotency_key=None, dry_run_mode=False):
        return {"anomaly_detected": True, "severity": 0.85,
                "anomaly_context": {"target_service": "emailservice"},
                "confidence": 0.92, "correlation_id": "corr-1"}

    def decide(self, correlation_id, anomaly_context, idempotency_key, dry_run_mode):
        return {"matched_runbook": "RestartDeploymentRunbook",
                "action_plan": [{"step": 1, "action": "RESTART_DEPLOYMENT",
                                 "target": "deployment/emailservice",
                                 "params": {"namespace": "onlineboutique-tnt-a",
                                            "estimated_pod_impact_pct": 10}}],
                "blast_radius_config": {"max_pod_impact_pct": 25,
                                        "allowed_namespaces": ["onlineboutique-tnt-a"]}}

    def verify(self, correlation_id, action_executed, post_telemetry_window,
               idempotency_key=None, dry_run_mode=False):
        if self.scenario == "regression":
            return {"success": False, "regression_detected": True, "next_action": "ROLLBACK"}
        if self.scenario == "escalate":
            return {"success": False, "regression_detected": False, "next_action": "ESCALATE"}
        return {"success": True, "regression_detected": False, "next_action": "DONE"}


@pytest.fixture(autouse=True)
def reset_breaker():
    # reset circuit breaker + locks giữa các test
    importlib.reload(guardrails)
    orchestrator._breaker = guardrails.CircuitBreaker()
    orchestrator._locks = guardrails.IdempotencyLock()


def test_resolved():
    out = orchestrator.run_remediation(SAMPLE, client=FakeEngine("normal"))
    assert out["outcome"] == "RESOLVED"


def test_regression_triggers_rollback_escalate():
    out = orchestrator.run_remediation(SAMPLE, client=FakeEngine("regression"))
    assert out["outcome"] == "ESCALATED"
    assert out["reason"] == "regression_rollback"


def test_engine_asks_escalate():
    out = orchestrator.run_remediation(SAMPLE, client=FakeEngine("escalate"))
    assert out["outcome"] == "ESCALATED"


def test_blast_radius_violation():
    class BadNS(FakeEngine):
        def decide(self, *a, **k):
            d = super().decide(*a, **k)
            d["action_plan"][0]["params"]["namespace"] = "kube-system"  # ngoài allowlist
            return d
    out = orchestrator.run_remediation(SAMPLE, client=BadNS("normal"))
    assert out["outcome"] == "ESCALATED"
    assert out["reason"] == "blast_radius_violation"


def test_503_fallback():
    from engine_client import EngineUnavailable

    class Down(FakeEngine):
        def detect(self, *a, **k):
            raise EngineUnavailable("down")
    out = orchestrator.run_remediation(SAMPLE, client=Down())
    assert out["outcome"] == "FALLBACK_STATIC_RUNBOOK"


def test_idempotency_duplicate_skipped():
    eng = FakeEngine("normal")
    # cùng idem_key không tái tạo được vì random; thay vào đó test acquire trực tiếp
    lock = guardrails.IdempotencyLock()
    assert lock.acquire("k1") is True
    assert lock.acquire("k1") is False


def test_low_confidence_escalates():
    class LowConf(FakeEngine):
        def detect(self, *a, **k):
            d = super().detect(*a, **k); d["confidence"] = 0.3; return d
    out = orchestrator.run_remediation(SAMPLE, client=LowConf("normal"))
    assert out["outcome"] == "ESCALATED"
    assert out["reason"] == "low_confidence"


def test_delete_pod_denied():
    class DelPod(FakeEngine):
        def decide(self, *a, **k):
            d = super().decide(*a, **k); d["action_plan"][0]["action"] = "DELETE_POD"; return d
    out = orchestrator.run_remediation(SAMPLE, client=DelPod("normal"))
    assert out["outcome"] == "ESCALATED"
    assert out["reason"] == "action_policy_violation"


def test_forbidden_namespace_denied():
    class SysNs(FakeEngine):
        def decide(self, *a, **k):
            d = super().decide(*a, **k)
            d["action_plan"][0]["params"]["namespace"] = "kube-system"
            d["blast_radius_config"]["allowed_namespaces"] = ["kube-system"]  # qua blast-radius để test action_policy
            return d
    out = orchestrator.run_remediation(SAMPLE, client=SysNs("normal"))
    assert out["outcome"] == "ESCALATED"
    assert out["reason"] == "action_policy_violation"


def test_missing_deployment_target_denied():
    # deployment-contract §1.5: action thao tác Deployment thiếu target → chặn
    class NoDep(FakeEngine):
        def decide(self, *a, **k):
            d = super().decide(*a, **k)
            d["action_plan"][0].pop("target", None)
            d["action_plan"][0]["params"].pop("deployment", None)
            return d
    out = orchestrator.run_remediation(SAMPLE, client=NoDep("normal"))
    assert out["outcome"] == "ESCALATED"
    assert out["reason"] == "target_topology_violation"


def test_target_outside_allowlist_denied():
    # cặp [ns, deployment] ngoài allowed_targets → chặn (contract §1.5)
    class BadTarget(FakeEngine):
        def decide(self, *a, **k):
            d = super().decide(*a, **k)
            d["blast_radius_config"]["allowed_targets"] = ["onlineboutique-tnt-a/cartservice"]
            return d  # target thực = emailservice → ngoài allowlist
    out = orchestrator.run_remediation(SAMPLE, client=BadTarget("normal"))
    assert out["outcome"] == "ESCALATED"
    assert out["reason"] == "target_topology_violation"


def test_deferred_creates_gitops_pr():
    class Deferred(FakeEngine):
        def decide(self, *a, **k):
            d = super().decide(*a, **k); d["pattern_type"] = "deferred"; return d
    out = orchestrator.run_remediation(SAMPLE, client=Deferred("normal"))
    assert out["outcome"] == "DEFERRED_GITOPS"


def test_forbidden_escalates():
    # 403 (tenant mismatch) → escalate, KHÔNG crash (ai-api §4 mới)
    from engine_client import EngineForbidden
    class Forbidden(FakeEngine):
        def detect(self, *a, **k): raise EngineForbidden("tenant mismatch")
    out = orchestrator.run_remediation(SAMPLE, client=Forbidden())
    assert out["outcome"] == "ESCALATED"
    assert out["reason"] == "tenant_forbidden"


def test_server_error_escalates():
    # 500 hết retry → escalate, KHÔNG crash
    from engine_client import EngineServerError
    class Err(FakeEngine):
        def detect(self, *a, **k): raise EngineServerError("500 after retries")
    out = orchestrator.run_remediation(SAMPLE, client=Err())
    assert out["outcome"] == "ESCALATED"
    assert out["reason"] == "engine_server_error"


def test_scale_to_zero_denied():
    # deployment §3.D: SCALE_REPLICAS replicas<1 bị chặn
    class Zero(FakeEngine):
        def decide(self, *a, **k):
            d = super().decide(*a, **k)
            d["action_plan"][0]["action"] = "SCALE_REPLICAS"
            d["action_plan"][0]["params"]["replicas"] = 0
            return d
    out = orchestrator.run_remediation(SAMPLE, client=Zero("normal"))
    assert out["outcome"] == "ESCALATED"
    assert out["reason"] == "action_policy_violation"


def test_rollback_called_on_regression(monkeypatch):
    # ai-api FINAL: AI KHÔNG cấp snapshot → CDO rollback từ pre_state tự capture.
    # Verify regression → executor.rollback được gọi với ActionResult (1 tham số).
    captured = {}
    def fake_rollback(result): captured["action"] = result.action
    monkeypatch.setattr(orchestrator, "rollback", fake_rollback)
    out = orchestrator.run_remediation(SAMPLE, client=FakeEngine("regression"))
    assert out["outcome"] == "ESCALATED"
    assert out["reason"] == "regression_rollback"
    assert captured["action"] == "RESTART_DEPLOYMENT"
