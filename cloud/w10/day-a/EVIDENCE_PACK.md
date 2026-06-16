# W10-D1 — Evidence Pack

Bằng chứng đã làm D1 RBAC + Admission Policy: 3 role với ranh giới quyền rõ
ràng, OPA/Gatekeeper 4 constraint (3 enforce + 1 audit), VAP native, demo
admission từ chối pod vi phạm và admit pod tuân thủ.

Môi trường:
- Cluster: minikube (Docker driver), Kubernetes ≥ v1.30 (cần cho VAP)
- Gatekeeper: release-3.17 (`kubectl apply --server-side --force-conflicts`)

## 1. RBAC — 3 role apply thành công

```powershell
kubectl apply -f cloud/w10/day-a/rbac/00-namespace.yaml
kubectl apply -f cloud/w10/day-a/rbac/viewer.yaml
kubectl apply -f cloud/w10/day-a/rbac/developer.yaml
kubectl apply -f cloud/w10/day-a/rbac/sre.yaml
```

![Apply RBAC — namespace, SA, role, binding created](screenshots/01-rbac-applied.png)

## 2. `auth can-i` — ma trận quyền đúng kỳ vọng

Chạy `rbac/test-can-i.ps1`, mọi dòng đánh dấu `OK` (kết quả khớp expect):

- viewer: `list pods` = yes, `create deployments` = no, `get secrets` = no
- developer: `create deployments` = yes, `get secrets` = yes,
  `create namespaces` = **no**, `create rolebindings` = **no**
- sre: `list nodes` = yes, `create k8srequiredlabels` = yes,
  `create clusterrolebindings` = **no**

![test-can-i.ps1 — ma trận quyền OK](screenshots/02-auth-can-i.png)

## 3. Gatekeeper — template sinh CRD, constraint áp dụng

```powershell
kubectl get constrainttemplates
kubectl get constraints
```

![ConstraintTemplate + Constraint](screenshots/03-gatekeeper-constraints.png)

4 constraint: 3 `deny` + `require-nonroot` ở `dryrun`.

## 4. Enforce — pod vi phạm bị TỪ CHỐI

```powershell
kubectl apply -f cloud/w10/day-a/policies/test/bad-pod.yaml
```

Admission từ chối, message liệt kê vi phạm (`:latest` + thiếu cpu/memory limit):

```text
Error from server (Forbidden): admission webhook "validation.gatekeeper.sh" denied the request:
[pods-no-latest-tag] container <app> dùng tag :latest (image nginx:latest) — phải pin version cụ thể
[pods-must-have-limits] container <app> thiếu cpu limit
[pods-must-have-limits] container <app> thiếu memory limit
```

![bad-pod bị Gatekeeper từ chối](screenshots/04-bad-pod-denied.png)

## 5. Compliant — good-pod được admit

```powershell
kubectl apply -f cloud/w10/day-a/policies/test/good-pod.yaml
kubectl -n w10-demo get pod good-pod
```

![good-pod Running](screenshots/05-good-pod-running.png)

## 6. Audit mode — pod vi phạm rule `dryrun` vẫn được ADMIT

Cách chứng minh trực tiếp audit-mode vs enforce: `audit-root-pod` chạy **root**
(vi phạm `require-nonroot`) nhưng pin tag + có resource limit (pass 3 rule `deny`
+ VAP). Vì `require-nonroot` ở `dryrun`, pod này **được admit và Running** —
trong khi `bad-pod` (mục 4) bị `deny`. Khác biệt nằm ở `enforcementAction`.

```powershell
kubectl apply -f cloud/w10/day-a/policies/test/audit-root-pod.yaml
kubectl -n w10-demo get pods
# audit-root-pod   1/1   Running   <- vi phạm non-root nhưng dryrun nên không chặn
```

![audit-root-pod Running dù vi phạm rule dryrun](screenshots/06-audit-root-pod-running.png)

Bổ sung: khi bật `gatekeeper-audit` (scale 1), số vi phạm hiện ở:

```powershell
kubectl get k8srequirerunasnonroot require-nonroot -o jsonpath='{.status.totalViolations}'
```

## 7. VAP native — CEL từ chối thiếu memory limit

Pod thiếu memory limit bị `ValidatingAdmissionPolicy` (không qua Gatekeeper) chặn:

```text
ValidatingAdmissionPolicy 'require-resource-limits' ... VAP: mọi container phải set memory limit
```

![VAP deny](screenshots/07-vap-deny.png)

## Kết luận

- RBAC tách 3 vai trò với ranh giới cố ý: developer không sờ namespace/RBAC,
  sre đọc nhưng không ghi RBAC (chống privilege escalation).
- `auth can-i` chứng minh phân quyền mà không cần login thật.
- Gatekeeper: 1 ConstraintTemplate (Rego) → CRD → N Constraint (instance).
- Admission chặn pod vi phạm **ở cluster level** — không dựa "developer hứa".
- Audit (`dryrun`) cho rollout an toàn: đo violation trước, flip `deny` sau.
- VAP native (CEL, 1.30+) làm cùng việc không cần webhook ngoài.
