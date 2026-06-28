# Manifests (K8s) — CDO-02 Self-Heal Platform (W12)

Deploy theo **GitOps (ArgoCD)** hoặc `kubectl apply`. Khớp [`../docs/04_deployment_design.md`](../docs/04_deployment_design.md) sync waves.

## Layout
```
manifests/platform/
├── ai-engine.yaml                # AI engine TỰ HOST (ns self-heal-system) + IRSA Bedrock + HPA — ADR-008
├── ai-engine-networkpolicy.yaml  # NetworkPolicy ingress 8080 từ controller / egress 443 VPC — contract §5
├── executor.yaml                 # Self-heal executor in-cluster (ns platform) — ADR-001/007
└── executor-rbac.yaml            # Role+RoleBinding least-privilege per tenant ns — contract §3.D
```
Engine namespace = `self-heal-system` (deployment-contract §2A); service DNS `ai-engine.self-heal-system.svc.cluster.local:8080` (§2C).
(tenant namespace + RBAC + NetworkPolicy: provision bằng Terraform `modules/tenant-provision`.)

## Prereq trước khi apply (W12)
1. **Bedrock model access**: bật `anthropic.claude-3-haiku-20240307-v1:0` trong Bedrock console (us-east-1) — account CDO-2.
2. **IAM IRSA roles** (thay `ACCOUNT_ID` trong manifest):
   - `tf-3-cdo2-ai-engine-bedrock-role`: chỉ `bedrock:InvokeModel` (+ stream) cho Claude 3 Haiku. KHÔNG có quyền EKS.
   - `tf-3-cdo2-executor-role`: `dynamodb:*Item` (idempotency) + `s3:PutObject` (audit prefix tenant).
3. **ECR images**: push image AI engine (AIO giao) + executor.

## Thứ tự apply
```bash
kubectl apply -f platform/ai-engine.yaml              # ns self-heal-system + SA + Deploy + HPA + Service
kubectl apply -f platform/ai-engine-networkpolicy.yaml # NetworkPolicy (contract §5)
kubectl -n self-heal-system rollout status deploy/ai-engine
kubectl apply -f platform/executor.yaml               # executor trỏ vào service engine
kubectl apply -f platform/executor-rbac.yaml          # Role+RoleBinding least-privilege (§3.D) — lặp cho mỗi tenant ns
```

## Bootstrap sớm (đầu W12, trước khi có image thật)
Trỏ executor vào **skeleton chung** của AIO để integrate code path:
```bash
kubectl -n platform set env deploy/self-heal-executor \
  ENGINE_BASE_URL="https://ai-engine-skeleton.tf-3.internal"
```

## ⚠️ Lưu ý
- Engine chỉ expose `/v1/*` (decide-only) — **không** cấp RBAC/kubeconfig vào workload tenant (ADR-007).
- Cost: Bedrock cap **$50/ngày/tenant** (engine tự enforce) + dùng $200 credit capstone. Teardown sau freeze.
