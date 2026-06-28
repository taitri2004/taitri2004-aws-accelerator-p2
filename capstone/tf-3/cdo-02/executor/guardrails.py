"""5 safety guardrail + idempotency lock. CDO ENFORCE, không chỉ nhận config từ engine."""
from __future__ import annotations
import time
import logging
from collections import deque
from dataclasses import dataclass

from config import CFG

log = logging.getLogger("guardrails")


@dataclass
class GuardResult:
    ok: bool
    reason: str = ""


# Action CDO cho phép thực thi (ai-api §3.2 enum). DELETE_POD bị CDO CẤM (chính sách CDO-02).
ALLOWED_ACTIONS = {"RESTART_DEPLOYMENT", "PATCH_MEMORY_LIMIT", "SCALE_REPLICAS",
                   "ROLLOUT_UNDO", "ROTATE_SECRET"}

# Namespace hệ thống cấm tuyệt đối — deny CỨNG phía CDO (defense-in-depth, không phụ thuộc engine).
FORBIDDEN_NAMESPACES = {"kube-system", "kube-public", "kube-node-lease",
                        "observability", "argocd", "self-heal-system", "platform"}

# Action thao tác trên Deployment → BẮT BUỘC có target deployment (deployment-contract §1.5).
# ROTATE_SECRET nhắm Secret nên miễn yêu cầu deployment.
DEPLOYMENT_TARGET_ACTIONS = {"RESTART_DEPLOYMENT", "PATCH_MEMORY_LIMIT",
                             "SCALE_REPLICAS", "ROLLOUT_UNDO"}


# ---- Action policy: allow-list action + cấm namespace hệ thống (CDO tự enforce) ----
def check_action_policy(action_plan: list[dict], blast_radius_config: dict) -> GuardResult:
    """Chặn action ngoài allow-list (vd DELETE_POD) + namespace hệ thống.
    Gộp thêm forbidden_namespaces engine trả (nếu có) — engine bảo gì CDO vẫn tự chặn cứng."""
    forbidden = FORBIDDEN_NAMESPACES | set(blast_radius_config.get("forbidden_namespaces", []))
    for step in action_plan:
        action = step.get("action")
        if action not in ALLOWED_ACTIONS:
            return GuardResult(False, f"action '{action}' bị CDO cấm (allow-list {sorted(ALLOWED_ACTIONS)})")
        ns = step.get("params", {}).get("namespace")
        if ns in forbidden:
            return GuardResult(False, f"namespace hệ thống '{ns}' cấm tuyệt đối")
        # deployment-contract §3.D: cấm scale về 0 (tránh tự tay hạ service xuống 0 pod)
        if action == "SCALE_REPLICAS":
            reps = step.get("params", {}).get("replicas")
            if reps is not None and reps < 1:
                return GuardResult(False, f"SCALE_REPLICAS replicas={reps} < 1 bị cấm (deployment §3.D)")
    return GuardResult(True)


# ---- Target topology: validate cặp [namespace, deployment] (deployment-contract §1.5) ----
def check_target_topology(action_plan: list[dict], blast_radius_config: dict) -> GuardResult:
    """CDO có nghĩa vụ validate [namespace, deployment] TRƯỚC khi execute, giữ trong blast radius.
    - Action thao tác Deployment phải có cả namespace + deployment.
    - Nếu engine/CDO cấp allowed_targets (list 'ns/dep') thì cặp phải thuộc allowlist."""
    allowed = set(blast_radius_config.get("allowed_targets", []))   # vd {"onlineboutique-tnt-a/emailservice"}
    for step in action_plan:
        action = step.get("action")
        params = step.get("params", {})
        ns = params.get("namespace")
        if not ns:
            return GuardResult(False, f"action '{action}' thiếu namespace (contract §1.5)")
        if action in DEPLOYMENT_TARGET_ACTIONS:
            # deployment có thể ở params.deployment hoặc field target "deployment/<name>" (ai-api)
            dep = params.get("deployment") or step.get("target")
            if not dep:
                return GuardResult(False, f"action '{action}' thiếu deployment (contract §1.5)")
            dep_name = dep.split("/", 1)[1] if dep.startswith("deployment/") else dep
            if allowed and f"{ns}/{dep_name}" not in allowed:
                return GuardResult(False, f"cặp [{ns}, {dep_name}] ngoài allowed_targets {sorted(allowed)}")
    return GuardResult(True)


# ---- Confidence gate (engine spec §5.4): confidence thấp → escalate cho người ----
def check_confidence(detect_resp: dict) -> GuardResult:
    c = detect_resp.get("confidence", 0.0)
    if c < CFG.confidence_min:
        return GuardResult(False, f"confidence {c} < ngưỡng {CFG.confidence_min}")
    return GuardResult(True)


# ---- Giới hạn payload gửi AI (engine spec §6: max ~4000 token) ----
def fit_telemetry_window(window: list[dict]) -> tuple[list[dict], int]:
    """Ước lượng ~4 ký tự/token; nếu vượt thì trim datapoint CŨ nhất, giữ mới nhất.
    Trả (window đã cắt, token ước lượng)."""
    import json

    def toks(w: list) -> int:
        return len(json.dumps(w, ensure_ascii=False)) // 4

    trimmed = list(window)
    while len(trimmed) > 1 and toks(trimmed) > CFG.max_telemetry_tokens:
        trimmed.pop(0)
    return trimmed, toks(trimmed)


# ---- Guardrail 2: Blast-radius + allowlist (Client: default-deny) ----
def check_blast_radius(action_plan: list[dict], blast_radius_config: dict) -> GuardResult:
    allowed = set(blast_radius_config.get("allowed_namespaces", []))
    max_pct = blast_radius_config.get("max_pod_impact_pct", 100)

    for step in action_plan:
        ns = step.get("params", {}).get("namespace")
        if allowed and ns not in allowed:
            return GuardResult(False, f"namespace '{ns}' NOT in allowlist {allowed}")
        # Ước lượng impact — bản thật query số pod hiện có của deployment
        est_pct = step.get("params", {}).get("estimated_pod_impact_pct", 0)
        if est_pct > max_pct:
            return GuardResult(False, f"pod impact {est_pct}% > max {max_pct}%")
    return GuardResult(True)


# ---- Guardrail 5: Circuit breaker (sliding window) ----
class CircuitBreaker:
    def __init__(self, window: int | None = None, threshold: float | None = None):
        self.window = window or CFG.cb_window
        self.threshold = threshold or CFG.cb_error_threshold
        self._results: deque[bool] = deque(maxlen=self.window)
        self.open = False

    def record(self, success: bool) -> None:
        self._results.append(success)
        if len(self._results) == self.window:
            err_rate = 1 - (sum(self._results) / self.window)
            if err_rate > self.threshold:
                self.open = True
                log.error("CIRCUIT OPEN: error_rate %.0f%% > %.0f%%",
                          err_rate * 100, self.threshold * 100)

    def allow(self) -> GuardResult:
        if self.open:
            return GuardResult(False, "circuit breaker OPEN — remediation halted")
        return GuardResult(True)


# ---- Guardrail 4: quyết định rollback từ verify response ----
def needs_rollback(verify_resp: dict) -> bool:
    return verify_resp.get("regression_detected") or verify_resp.get("next_action") == "ROLLBACK"


# ---- Idempotency lock (deployment §5.A): conditional write, trùng → 409 ----
class IdempotencyLock:
    """memory mode cho dev; dynamodb mode cho thật (conditional write TTL 5p)."""
    def __init__(self):
        self.mode = CFG.idempotency_mode
        self._mem: dict[str, float] = {}

    def acquire(self, key: str, ttl_s: int = 300) -> bool:
        if self.mode == "dynamodb":
            return self._acquire_ddb(key, ttl_s)
        now = time.time()
        exp = self._mem.get(key)
        if exp and exp > now:
            return False                 # đang chạy → từ chối (409)
        self._mem[key] = now + ttl_s
        return True

    def _acquire_ddb(self, key: str, ttl_s: int) -> bool:
        import boto3
        from botocore.exceptions import ClientError
        ddb = boto3.client("dynamodb", region_name=CFG.aws_region)
        try:
            ddb.put_item(
                TableName=CFG.idempotency_table,
                Item={"idempotency_key": {"S": key},
                      "expires_at": {"N": str(int(time.time()) + ttl_s)}},
                ConditionExpression="attribute_not_exists(idempotency_key)",
            )
            return True
        except ClientError as e:
            if e.response["Error"]["Code"] == "ConditionalCheckFailedException":
                return False
            raise
