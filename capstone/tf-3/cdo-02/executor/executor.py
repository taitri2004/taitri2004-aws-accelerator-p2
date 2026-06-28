"""Thực thi action_plan lên K8s. mock mode = log; live mode = kubernetes client.

Action enum (ai-api §3.2, contract 25/06): RESTART_DEPLOYMENT, PATCH_MEMORY_LIMIT,
SCALE_REPLICAS, ROLLOUT_UNDO, ROTATE_SECRET. (DELETE_POD bị CDO cấm — chặn ở guardrails.)
"""
from __future__ import annotations
import logging
from dataclasses import dataclass, field

from config import CFG

log = logging.getLogger("executor")

SUPPORTED = {"RESTART_DEPLOYMENT", "PATCH_MEMORY_LIMIT", "SCALE_REPLICAS",
             "ROLLOUT_UNDO", "ROTATE_SECRET"}


@dataclass
class ActionResult:
    action: str
    target: str
    status: str                       # COMPLETED | FAILED | DRY_RUN
    execution_time_seconds: float = 0.0
    pre_state: dict = field(default_factory=dict)   # snapshot để rollback
    error: str = ""


def execute_action(step: dict, dry_run: bool) -> ActionResult:
    action = step["action"]
    target = step.get("target", "")
    if action not in SUPPORTED:
        return ActionResult(action, target, "FAILED", error=f"unsupported action {action}")

    if dry_run:
        log.info("[DRY-RUN] would %s on %s params=%s", action, target, step.get("params"))
        return ActionResult(action, target, "DRY_RUN")

    if CFG.execute_mode == "live":
        return _execute_live(step)
    # mock mode
    log.info("[MOCK-EXEC] %s on %s params=%s", action, target, step.get("params"))
    return ActionResult(action, target, "COMPLETED", execution_time_seconds=1.0,
                        pre_state={"note": "mock pre-state snapshot"})


def propose_gitops_change(step: dict) -> ActionResult:
    """pattern_type=deferred (Path A GitOps): KHÔNG ghi thẳng cluster (ai-api §3.2).
    Tạo PR cập nhật manifest/Helm values; ArgoCD/Flux sync sau. Mock = log."""
    action, target = step["action"], step.get("target", "")
    log.info("[GITOPS-PR] mở PR cập nhật manifest cho %s on %s params=%s",
             action, target, step.get("params"))
    return ActionResult(action, target, "DEFERRED_PR",
                        pre_state={"note": "gitops PR proposed (mock)"})


def rollback(result: ActionResult) -> None:
    """Auto-rollback (guardrail 4). ai-api FINAL: AI KHÔNG cấp snapshot → CDO dùng
    `pre_state` tự capture TRƯỚC khi execute (replicas/memory/image/namespace). Mock = log; live = revert."""
    log.warning("ROLLBACK %s on %s → restore pre_state=%s",
                result.action, result.target, result.pre_state)
    if CFG.execute_mode == "live":
        _rollback_live(result)


# ---- live K8s (chỉ chạy khi EXECUTE_MODE=live) ----
def _k8s_apps():
    from kubernetes import client, config as kcfg
    # K8s-heavy: executor chạy TRONG cluster → in-cluster SA (no kubeconfig, ADR-007).
    # Fallback load_kube_config() chỉ cho dev local ngoài cluster.
    try:
        kcfg.load_incluster_config()
    except kcfg.ConfigException:
        kcfg.load_kube_config()
    return client.AppsV1Api()

def _execute_live(step: dict) -> ActionResult:
    import time
    action, target = step["action"], step["target"]
    params = step.get("params", {})
    ns = params["namespace"]
    name = target.split("/")[-1]
    apps = _k8s_apps()
    t0 = time.time()
    try:
        dep = apps.read_namespaced_deployment(name, ns)
        # snapshot pre-state cho rollback (replicas + memory limit container đầu)
        cont0 = dep.spec.template.spec.containers[0]
        # pre-state = snapshot CDO tự capture trước khi patch (ai-api FINAL: AI không cấp)
        pre = {"namespace": ns, "replicas": dep.spec.replicas, "image": cont0.image,
               "memory_limit": (cont0.resources.limits or {}).get("memory") if cont0.resources else None}
        if action == "RESTART_DEPLOYMENT":
            # patch annotation để trigger rolling restart
            patch = {"spec": {"template": {"metadata": {"annotations":
                     {"selfheal/restartedAt": str(int(t0))}}}}}
            apps.patch_namespaced_deployment(name, ns, patch)
        elif action == "SCALE_REPLICAS":
            apps.patch_namespaced_deployment_scale(
                name, ns, {"spec": {"replicas": params["replicas"]}})
        elif action == "PATCH_MEMORY_LIMIT":
            container = params.get("container", name)
            limits = {}
            if params.get("memory_limit_mb"):
                limits["memory"] = f"{params['memory_limit_mb']}Mi"
            requests_ = {}
            if params.get("memory_request_mb"):
                requests_["memory"] = f"{params['memory_request_mb']}Mi"
            patch = {"spec": {"template": {"spec": {"containers":
                     [{"name": container, "resources": {"limits": limits, "requests": requests_}}]}}}}
            apps.patch_namespaced_deployment(name, ns, patch)
        elif action == "ROLLOUT_UNDO":
            # rollback về revision trước: trigger qua annotation rollout (bản thật dùng Argo Rollouts/kubectl)
            patch = {"spec": {"template": {"metadata": {"annotations":
                     {"selfheal/rolloutUndoAt": str(int(t0))}}}}}
            apps.patch_namespaced_deployment(name, ns, patch)
        elif action == "ROTATE_SECRET":
            # rotate qua ESO/Secrets Manager (rút gọn ở skeleton); chỉ đánh dấu để verify
            log.warning("ROTATE_SECRET %s — delegate to ESO/Secrets Manager", params.get("secret_name"))
        return ActionResult(action, target, "COMPLETED", time.time() - t0, pre_state=pre)
    except Exception as e:  # noqa
        return ActionResult(action, target, "FAILED", error=str(e))

def _rollback_live(result: ActionResult) -> None:
    """Revert thật từ pre_state CDO tự capture (ai-api FINAL: AI không cấp snapshot)."""
    pre = result.pre_state or {}
    ns = pre.get("namespace", "default")
    name = result.target.split("/")[-1]
    apps = _k8s_apps()
    try:
        if result.action == "SCALE_REPLICAS" and pre.get("replicas") is not None:
            apps.patch_namespaced_deployment_scale(name, ns, {"spec": {"replicas": pre["replicas"]}})
            log.warning("rollback replicas→%s (%s/%s)", pre["replicas"], ns, name)
        elif result.action == "PATCH_MEMORY_LIMIT" and pre.get("memory_limit"):
            patch = {"spec": {"template": {"spec": {"containers":
                     [{"name": name, "resources": {"limits": {"memory": pre["memory_limit"]}}}]}}}}
            apps.patch_namespaced_deployment(name, ns, patch)
            log.warning("rollback memory→%s (%s/%s)", pre["memory_limit"], ns, name)
        elif result.action == "ROLLOUT_UNDO" and pre.get("image"):
            patch = {"spec": {"template": {"spec": {"containers":
                     [{"name": name, "image": pre["image"]}]}}}}
            apps.patch_namespaced_deployment(name, ns, patch)
            log.warning("rollback image→%s (%s/%s)", pre["image"], ns, name)
        else:
            # RESTART/ROTATE_SECRET hoặc thiếu snapshot → không revert an toàn được → escalate
            log.warning("rollback: không revert tự động được cho %s (%s) — cần escalate", result.action, result.target)
    except Exception as e:  # noqa
        log.error("rollback live FAILED %s: %s", result.target, e)
