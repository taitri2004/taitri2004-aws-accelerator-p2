# Ký image với Cosign + bật verify ở admission (Kyverno)

## Cài Kyverno

```powershell
helm repo add kyverno https://kyverno.github.io/kyverno; helm repo update
helm install kyverno kyverno/kyverno -n kyverno --create-namespace
kubectl -n kyverno rollout status deploy/kyverno-admission-controller
```

## Ký image

```powershell
# Keyless (CI / có OIDC) — danh tính từ GitHub Actions, cert ngắn hạn Fulcio,
# log vào Rekor. Không giữ khoá.
cosign sign ghcr.io/taitri2004/w10-app@sha256:<digest>

# Key-based (offline) — sinh cặp khoá rồi ký bằng private key.
cosign generate-key-pair
cosign sign --key cosign.key ghcr.io/taitri2004/w10-app@sha256:<digest>
# -> dán nội dung cosign.pub vào verify-key.yaml
```

> Luôn ký theo **digest** (`@sha256:...`), không theo tag (tag có thể bị đẩy lại).

## Bật verify ở admission

```powershell
# Chọn 1: keyless (khớp CI) hoặc key-based
kubectl apply -f cloud/w10/day-b/signing/verify-keyless.yaml
# hoặc: kubectl apply -f cloud/w10/day-b/signing/verify-key.yaml
```

## Kiểm chứng

```powershell
# Image CHƯA ký / ký sai danh tính -> REJECT
kubectl apply -f cloud/w10/day-b/signing/test/unsigned-pod.yaml   # bị từ chối

# Image đã ký đúng -> ADMIT (chạy sau khi CI sign image)
```

## Exception (break-glass)

Khi buộc phải chạy image chưa ký (vendor cũ...), tạo exception **có hạn + có
chủ**, ghi ADR:

```powershell
kubectl apply -f cloud/w10/day-b/signing/policy-exception.yaml
```

Xem `adr/0001-image-signing-and-exceptions.md`.
