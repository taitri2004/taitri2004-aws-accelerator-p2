# Runbook: Secret rotation lỗi / app dùng giá trị cũ

- **Mức độ:** SEV-2
- **Chủ:** platform-team
- **Cập nhật:** 2026-06-17

## Triệu chứng
- Đã đổi secret ở AWS Secrets Manager nhưng app vẫn dùng giá trị cũ (auth fail),
  hoặc `ExternalSecret` status `SecretSyncedError`.

## Tác động
- App không kết nối được DB/dịch vụ phụ thuộc secret vừa rotate.

## Cách phát hiện / chẩn đoán
```bash
kubectl -n <ns> get externalsecret <name>
kubectl -n <ns> describe externalsecret <name>   # xem reason/lỗi auth IRSA
kubectl -n <ns> get secret <target> -o jsonpath='{.metadata.resourceVersion}'
```

## Các bước xử lý
1. **Nếu app dùng env (không phải volume)**: env chốt lúc start → rotate KHÔNG
   ăn cho tới khi restart. Cách đúng: mount secret dạng volume. Mitigate nhanh:
   `kubectl -n <ns> rollout restart deploy/<app>`.
2. **Nếu `SecretSyncedError`**: kiểm IRSA/SA quyền `secretsmanager:GetSecretValue`,
   region, tên secret/property đúng không.
3. **Ép sync ngay** (không chờ refreshInterval):
   ```bash
   kubectl -n <ns> annotate externalsecret <name> force-sync=$(Get-Date -Format o) --overwrite
   ```
4. **Xác nhận**: giá trị file mount đổi sang mới; app hết auth fail.

## Leo thang
- Secret production (DB prod) sai > 15 phút → báo owner dịch vụ.

## Sau sự cố
- Nếu nguyên nhân là dùng env thay vì volume → sửa deployment (no-restart rotation).
