# W10 — Day B: Secrets Rotation + Supply Chain

Scope D2: External Secrets Operator + AWS Secrets Manager (rotation < 60s,
no-restart), Trivy scan trong CI (fail HIGH/CRITICAL), Cosign signing (keyless
OIDC + key-based), verify signature ở admission (Kyverno), exception CVE có hạn.
Tài liệu nền: [`knowledge/w10-foundation-rbac-secrets-platform.md`](../../../knowledge/w10-foundation-rbac-secrets-platform.md) §7–§12.

Tinh thần: secret không nằm trong Git; cluster chỉ chạy image **đã quét + đã ký**.

## Layout

```
day-b/
  README.md
  notes.md                    Ghi chú self-study D2
  EVIDENCE_PACK.md            Bằng chứng (screenshot + log)
  screenshots/
  eso/
    00-namespace.yaml         ns w10-secrets + SA IRSA
    secretstore-aws.yaml      ClusterSecretStore -> AWS Secrets Manager (IRSA)
    externalsecret-aws.yaml   ExternalSecret (refreshInterval 10s)
    secretstore-fake.yaml     Provider fake cho demo offline
    externalsecret-fake.yaml
    consumer-deployment.yaml  Mount secret dạng volume -> rotation no-restart
    install.md
  signing/
    sign.md                   Cosign sign + bật verify
    verify-keyless.yaml       Kyverno verifyImages keyless (OIDC)
    verify-key.yaml           Kyverno verifyImages key-based
    policy-exception.yaml     PolicyException break-glass có hạn
    adr/                      ADR quyết định ký + exception
    test/unsigned-pod.yaml    Image chưa ký -> reject
  ci-trivy/
    Dockerfile + app.py       Image mẫu để quét + ký
    .trivyignore              CVE miễn có hạn
```

CI: `.github/workflows/supply-chain-w10-day-b.yml` (build + Trivy + Cosign),
`validate-w10-day-b.yml` (kubeconform).

## Mục tiêu D2 (acceptance)

| # | Yêu cầu | Artifact |
|---|---|---|
| 1 | ESO sync secret từ store ngoài | `eso/secretstore-*.yaml` + `externalsecret-*.yaml` |
| 2 | Rotation < 60s, không restart pod | `eso/consumer-deployment.yaml` (volume mount) |
| 3 | Trivy CI fail-on HIGH/CRITICAL | `.github/workflows/supply-chain-w10-day-b.yml` |
| 4 | Cosign sign keyless + key-based | `signing/sign.md` + workflow sign step |
| 5 | Admission reject unsigned image | `signing/verify-keyless.yaml` + `test/unsigned-pod.yaml` |
| 6 | Exception CVE/signature có hạn | `ci-trivy/.trivyignore` + `signing/policy-exception.yaml` + ADR |

## Run

```powershell
# ESO (chi tiết: eso/install.md) — đường offline (provider fake)
helm install external-secrets external-secrets/external-secrets `
  -n external-secrets --create-namespace --set installCRDs=true
kubectl apply -f cloud/w10/day-b/eso/00-namespace.yaml
kubectl apply -f cloud/w10/day-b/eso/secretstore-fake.yaml
kubectl apply -f cloud/w10/day-b/eso/externalsecret-fake.yaml
kubectl apply -f cloud/w10/day-b/eso/consumer-deployment.yaml
kubectl -n w10-secrets logs -f deploy/secret-consumer   # xem rotation

# Signing (chi tiết: signing/sign.md)
helm install kyverno kyverno/kyverno -n kyverno --create-namespace
kubectl apply -f cloud/w10/day-b/signing/verify-keyless.yaml
kubectl apply -f cloud/w10/day-b/signing/test/unsigned-pod.yaml   # reject
```

Bằng chứng: `EVIDENCE_PACK.md`. Bẫy khi chạy thật: `notes.md` §6.
