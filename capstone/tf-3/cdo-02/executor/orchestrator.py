"""Orchestrator — mirror Step Functions state machine (ADR-001).

Flow: Detect → Decide → [Dry-run gate] → [Blast-radius] → [Circuit breaker]
      → [Idempotency] → Execute → Verify → Choice(DONE/RETRY/ROLLBACK/ESCALATE)
Mỗi state ghi audit. 503 → fallback. Đây là logic sẽ bê lên SFN/Lambda W12.
"""
from __future__ import annotations
import uuid
import time
import logging

from config import CFG
from engine_client import (EngineClient, EngineUnavailable, EngineBadRequest,
                           EngineConflict, EngineRateLimited,
                           EngineForbidden, EngineServerError)
from guardrails import (check_blast_radius, check_action_policy, check_confidence,
                        check_target_topology, fit_telemetry_window,
                        CircuitBreaker, IdempotencyLock)
from executor import execute_action, rollback, propose_gitops_change
from audit import AuditLogger

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
log = logging.getLogger("orchestrator")

_breaker = CircuitBreaker()
_locks = IdempotencyLock()


def run_remediation(alert: dict, client: EngineClient | None = None) -> dict:
    """alert = {telemetry_window: [...]}. Trả outcome dict."""
    client = client or EngineClient()
    correlation_id = str(uuid.uuid4())
    # idem_key = khóa INCIDENT-LEVEL cho execution-lock (chống double-execute 1 incident).
    # Mỗi call engine (detect/decide/verify) dùng Idempotency-Key RIÊNG (REST-đúng,
    # tránh engine 409 vì key đã thấy ở call trước).
    idem_key = str(uuid.uuid4())
    audit = AuditLogger(CFG.tenant_id, correlation_id)

    # Đo latency từng state + tổng (ms) — evidence cho 07_test_eval, không ảnh hưởng logic.
    _t0 = time.perf_counter()
    _prev = [_t0]
    _marks: dict[str, float] = {}

    def _mark(name: str) -> None:
        now = time.perf_counter()
        _marks[name] = round((now - _prev[0]) * 1000, 1)
        _prev[0] = now

    def _latency() -> dict:
        return {**_marks, "total_ms": round((time.perf_counter() - _t0) * 1000, 1)}

    # Guardrail 5: circuit breaker mở → dừng ngay
    cb = _breaker.allow()
    if not cb.ok:
        audit.write("circuit_breaker", {"halted": True, "reason": cb.reason})
        return _escalate(audit, "circuit_open", cb.reason)

    try:
        # --- Giới hạn payload trước khi gửi AI (engine spec §6: max ~4000 token) ---
        window, est_tokens = fit_telemetry_window(alert["telemetry_window"])
        if len(window) < len(alert["telemetry_window"]):
            audit.write("telemetry_trim", {"kept": len(window),
                        "orig": len(alert["telemetry_window"]), "est_tokens": est_tokens})

        # --- STATE: Detect ---
        det = client.detect(window, correlation_id, str(uuid.uuid4()), CFG.dry_run)
        _mark("detect_ms")
        # Adopt correlation_id của engine NGAY để mọi audit (kể cả detect) nhất quán
        correlation_id = det.get("correlation_id", correlation_id)
        audit.correlation_id = correlation_id
        audit.write("detect", det)
        if not det.get("anomaly_detected"):
            audit.write("done", {"reason": "no anomaly"})
            return {"outcome": "NO_ANOMALY", "correlation_id": correlation_id}

        # --- Guardrail confidence (engine spec §5.4): thấp → escalate cho người ---
        conf = check_confidence(det)
        audit.write("guardrail_confidence", {"ok": conf.ok, "reason": conf.reason})
        if not conf.ok:
            return _escalate(audit, "low_confidence", conf.reason)

        # --- STATE: Decide ---
        dec = client.decide(correlation_id, det["anomaly_context"], str(uuid.uuid4()), CFG.dry_run)
        _mark("decide_ms")
        audit.write("decide", dec)
        plan = dec.get("action_plan", [])
        brc = dec.get("blast_radius_config", {})
        # verify_policy do engine quyết (ai-api §3.2): chờ window_seconds rồi mới thu post-telemetry.
        # Fallback CFG nếu engine không trả. pattern_type: urgent (vá trực tiếp) / deferred (GitOps).
        vpol = dec.get("verify_policy", {})
        verify_window = vpol.get("window_seconds", CFG.verify_window_seconds)
        on_fail = vpol.get("on_fail")            # chỉ thị khi verify fail (ai-api §3.2)
        pattern_type = dec.get("pattern_type")
        # ROLLBACK snapshot (ai-api FINAL signed): AI KHÔNG trả rollback_snapshot (không có
        # quyền K8s API). CDO TỰ capture pre-state TRƯỚC khi execute — executor._execute_live
        # lưu vào ActionResult.pre_state (urgent); deferred ghi Git SHA. Dùng để revert khi verify→ROLLBACK.

        # --- Guardrail 2: Blast-radius + allowlist ---
        gr = check_blast_radius(plan, brc)
        audit.write("guardrail_blast_radius", {"ok": gr.ok, "reason": gr.reason})
        if not gr.ok:
            return _escalate(audit, "blast_radius_violation", gr.reason)

        # --- Guardrail action policy: allow-list action + cấm namespace hệ thống ---
        ap = check_action_policy(plan, brc)
        audit.write("guardrail_action_policy", {"ok": ap.ok, "reason": ap.reason})
        if not ap.ok:
            return _escalate(audit, "action_policy_violation", ap.reason)

        # --- Guardrail target topology: validate [namespace, deployment] (contract §1.5) ---
        tt = check_target_topology(plan, brc)
        audit.write("guardrail_target_topology", {"ok": tt.ok, "reason": tt.reason})
        if not tt.ok:
            return _escalate(audit, "target_topology_violation", tt.reason)

        # --- Guardrail 1: Dry-run gate ---
        if CFG.dry_run:
            for step in plan:
                execute_action(step, dry_run=True)
            audit.write("dry_run", {"plan": plan})
            return {"outcome": "DRY_RUN", "correlation_id": correlation_id, "plan": plan}

        # --- Idempotency lock ---
        if not _locks.acquire(idem_key):
            audit.write("idempotency", {"conflict": True, "key": idem_key})
            return {"outcome": "DUPLICATE_SKIPPED", "correlation_id": correlation_id}

        # --- pattern_type=deferred → Path A GitOps: tạo PR, KHÔNG ghi thẳng cluster (ai-api §3.2) ---
        if pattern_type == "deferred":
            for step in plan:
                p = propose_gitops_change(step)
                audit.write("gitops_propose", p.__dict__)
            audit.write("done", {"deferred_gitops": True})
            audit.write("latency", _latency())
            return {"outcome": "DEFERRED_GITOPS", "correlation_id": correlation_id,
                    "plan": plan, "latency_ms": _latency()}

        # --- STATE: Execute (urgent / Path B - vá trực tiếp) ---
        results = []
        for step in plan:
            r = execute_action(step, dry_run=False)
            audit.write("execute", r.__dict__)
            results.append(r)
            if r.status == "FAILED":
                _breaker.record(False)
                rollback(r)                      # revert từ pre_state CDO tự capture
                return _escalate(audit, "execute_failed", r.error, results)
        _mark("execute_ms")

        # --- STATE: Verify (Guardrail 3) ---
        action_executed = {"action": results[0].action, "target": results[0].target,
                           "status": "COMPLETED",
                           "execution_time_seconds": results[0].execution_time_seconds}
        # bản thật: chờ verify_window (engine quyết) rồi mới query post-telemetry
        post_window = alert.get("post_telemetry_window", [])
        audit.write("verify_wait", {"window_seconds": verify_window, "pattern_type": pattern_type})
        ver = client.verify(correlation_id, action_executed, post_window, str(uuid.uuid4()), CFG.dry_run)
        _mark("verify_ms")
        audit.write("verify", ver)
        audit.write("latency", _latency())

        # --- Choice --- next_action từ verify ưu tiên; fallback verify_policy.on_fail ---
        nxt = ver.get("next_action") or on_fail
        if ver.get("regression_detected") or nxt == "ROLLBACK":   # Guardrail 4
            for r in results:
                rollback(r)                      # revert từ pre_state CDO tự capture
            _breaker.record(False)
            return _escalate(audit, "regression_rollback", f"verify → {nxt}", results)
        if ver.get("success") and nxt == "DONE":
            _breaker.record(True)
            audit.write("done", {"auto_resolved": True})
            return {"outcome": "RESOLVED", "correlation_id": correlation_id,
                    "latency_ms": _latency()}
        if nxt == "RETRY":
            audit.write("retry", {})
            return {"outcome": "RETRY", "correlation_id": correlation_id}
        # ESCALATE
        _breaker.record(False)
        return _escalate(audit, "verify_escalate", f"verify → {nxt}",
                         results, ver.get("escalation_bundle"))

    # --- Error handling (ai-api §4) ---
    except EngineUnavailable as e:               # 503 → BẮT BUỘC fallback
        audit.write("engine_503", {"error": str(e)})
        return _fallback(audit, str(e))
    except EngineRateLimited as e:               # 429 hết retry
        audit.write("engine_429", {"error": str(e)})
        return _escalate(audit, "rate_limited", str(e))
    except EngineBadRequest as e:                # 400/422 → fix code, không retry
        audit.write("engine_400", {"error": str(e)})
        return {"outcome": "BAD_REQUEST", "error": str(e)}
    except EngineForbidden as e:                 # 403 → tenant mismatch, escalate (no retry)
        audit.write("engine_403", {"error": str(e)})
        return _escalate(audit, "tenant_forbidden", str(e))
    except EngineServerError as e:               # 500 hết retry → escalate
        audit.write("engine_500", {"error": str(e)})
        return _escalate(audit, "engine_server_error", str(e))
    except EngineConflict as e:                  # 409
        audit.write("engine_409", {"error": str(e)})
        return {"outcome": "DUPLICATE_SKIPPED", "error": str(e)}


def _escalate(audit: AuditLogger, reason: str, detail: str,
              results=None, bundle=None) -> dict:
    payload = {"reason": reason, "detail": detail, "bundle": bundle}
    audit.write("escalate", payload)
    _send_slack(f"[Self-Heal ESCALATE] {reason}: {detail}")
    return {"outcome": "ESCALATED", "reason": reason}


def _fallback(audit: AuditLogger, detail: str) -> dict:
    """503 fallback: chạy static runbook hoặc escalate thẳng (ai-api §4)."""
    audit.write("fallback", {"mode": "static_runbook", "detail": detail})
    _send_slack(f"[Self-Heal FALLBACK] engine down → static runbook. {detail}")
    return {"outcome": "FALLBACK_STATIC_RUNBOOK"}


def _send_slack(msg: str) -> None:
    if not CFG.slack_webhook:
        log.info("[SLACK-MOCK] %s", msg)
        return
    import requests
    requests.post(CFG.slack_webhook, json={"text": msg}, timeout=3)


if __name__ == "__main__":
    # Demo 1 vòng với telemetry mẫu (OOM-ish)
    sample_alert = {
        "telemetry_window": [
            {"ts": "2026-06-25T10:00:00.123Z", "signal_name": "container_resource_usage",
             "value": 503316480, "labels": {"service": "emailservice", "namespace": "onlineboutique-tnt-a",
                                            "deployment": "emailservice"}},
            {"ts": "2026-06-25T10:00:05.456Z", "signal_name": "service_error_rate",
             "value": 0.42, "labels": {"service": "emailservice", "namespace": "onlineboutique-tnt-a",
                                       "deployment": "emailservice"}},
        ],
        "post_telemetry_window": [
            {"ts": "2026-06-25T10:05:00.000Z", "signal_name": "service_error_rate",
             "value": 0.0, "labels": {"service": "emailservice"}},
        ],
    }
    outcome = run_remediation(sample_alert)
    print("\n=== OUTCOME ===", outcome)
