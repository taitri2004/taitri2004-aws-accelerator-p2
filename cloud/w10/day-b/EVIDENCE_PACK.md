# W10-D2 — Evidence Pack

Bằng chứng D2 Secrets Rotation + Supply Chain: ESO sync secret từ store ngoài,
rotation < 60s không restart pod, Trivy scan fail HIGH/CRITICAL trong CI, Cosign
ký image, admission từ chối image chưa ký, exception có thời hạn.

Môi trường:
- Cluster: minikube (Docker driver), ESO (chart external-secrets), Kyverno
- Supply chain CI: GitHub Actions (Trivy + Cosign keyless)

## 1. ESO sinh Secret K8s từ store ngoài

`ExternalSecret app-secret` đọc từ store (fake / AWS SM) và tạo `Secret app-secret`.

```powershell
kubectl -n w10-secrets get externalsecret,secret
kubectl -n w10-secrets get externalsecret app-secret -o jsonpath='{.status.conditions[0].reason}'
# -> SecretSynced
```

![ExternalSecret SecretSynced + Secret app-secret](screenshots/01-eso-synced.png)

## 2. Rotation < 60s, pod KHÔNG restart

Consumer mount secret dạng volume, in giá trị mỗi 5s. Đổi value ở store (fake:
`v1-rotate-me` → `v2-rotated`), trong < 60s log đổi sang giá trị mới mà
`RESTARTS` giữ nguyên 0.

```text
10:20:01 db-password = v1-rotate-me
10:20:31 db-password = v2-rotated      <- sau khi rotate, KHÔNG restart
```

![log consumer đổi giá trị + RESTARTS=0](screenshots/02-rotation-no-restart.png)

## 3. Trivy scan trong CI — fail HIGH/CRITICAL

Workflow `supply-chain-w10-day-b` build image rồi Trivy quét `--severity
HIGH,CRITICAL --exit-code 1`. CVE nghiêm trọng → job đỏ; sạch → xanh.

![Trivy step trong GitHub Actions](screenshots/03-trivy-ci.png)

## 4. Cosign ký image (keyless)

CI ký image theo digest bằng OIDC GitHub Actions (Fulcio + Rekor), không giữ khoá.

```text
cosign sign ghcr.io/taitri2004/w10-app@sha256:...
tlog entry created with index: ...
```

![Cosign sign step + Rekor entry](screenshots/04-cosign-sign.png)

## 5. Admission reject image chưa ký

Kyverno `verify-image-keyless` enforce. Pod dùng image chưa ký bị từ chối:

```text
Error from server: ... policy verify-image-keyless ... failed to verify image
ghcr.io/taitri2004/w10-app:unsigned: no matching signatures
```

![unsigned-pod bị Kyverno từ chối](screenshots/05-unsigned-rejected.png)

## 6. Exception có thời hạn

`.trivyignore` (CVE) và `PolicyException` (signature) đều ghi `owner` + `expiry`
+ lý do; có ADR. Quá hạn phải xoá.

![PolicyException + .trivyignore có expiry](screenshots/06-exception.png)

## Kết luận

- Secret không nằm trong Git; nguồn sự thật là store ngoài, ESO sync về.
- Rotation no-restart đạt được nhờ mount volume (không dùng env).
- Supply chain: Trivy chặn CVE ở CI, Cosign ký, admission chỉ chạy image đã ký.
- Exception luôn có chủ + hạn + lý do, không tắt vĩnh viễn.
