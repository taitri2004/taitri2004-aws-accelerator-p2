# Runbook: Admission webhook chặn mọi deploy

- **Mức độ:** SEV-2 (không deploy được, dịch vụ đang chạy vẫn sống)
- **Chủ:** platform-team
- **Cập nhật:** 2026-06-17

## Triệu chứng
- `kubectl apply` lỗi: `failed calling webhook ... connection refused` hoặc
  `Internal error occurred: ... admission webhook`.
- Pod mới không tạo được; ArgoCD app kẹt `Progressing`.

## Tác động
- Mọi thay đổi vào namespace bị webhook quản đều đứng. Workload cũ vẫn chạy.

## Cách phát hiện / chẩn đoán
```bash
kubectl get validatingwebhookconfiguration,mutatingwebhookconfiguration
# webhook nào failurePolicy=Fail mà backend chết -> thủ phạm
kubectl -n gatekeeper-system get pods        # controller có Ready không
kubectl -n kyverno get pods
```

## Các bước xử lý
1. **Mitigate ngay**: nếu controller chết và đang chặn production, đưa backend
   sống lại (scale lên) HOẶC tạm hạ `failurePolicy: Ignore` cho webhook đó.
   Bí quá: xoá webhook configuration (Gatekeeper/Kyverno tự tạo lại khi controller
   khỏe) — chấp nhận MẤT enforcement tạm thời.
   ```bash
   kubectl -n gatekeeper-system scale deploy/gatekeeper-controller-manager --replicas=1
   ```
2. **Root cause**: vì sao backend chết — OOM/thiếu CPU (xem `kubectl describe`),
   image pull lỗi, hay cert webhook hết hạn.
3. **Xác nhận hồi**: apply lại một pod test thành công; ArgoCD về Synced.

## Leo thang
- Sau 15 phút chưa deploy lại được và đang chặn release gấp → DM mentor/owner.

## Sau sự cố
- Nếu phải hạ `failurePolicy` hay xoá webhook: nhớ KHÔI PHỤC enforcement sau khi
  controller khỏe. Mở postmortem.
