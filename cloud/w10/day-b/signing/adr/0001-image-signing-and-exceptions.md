# ADR 0001 — Verify chữ ký image ở admission + cơ chế exception có thời hạn

> ADR (Architecture Decision Record) = ghi lại MỘT quyết định kiến trúc:
> bối cảnh, lựa chọn, lý do, hệ quả.

- **Trạng thái:** Accepted
- **Ngày:** 2026-06-16
- **Người quyết định:** taitri2004

## Bối cảnh (Context)
Image có thể bị thay/đầu độc giữa lúc build và lúc chạy. Quét CVE (Trivy) ở CI là
cần nhưng chưa đủ: registry vẫn có thể nhận image lạ. Cần một chốt chặn ở chính
cluster để chỉ image đã ký bởi pipeline tin cậy mới được chạy.

## Quyết định (Decision)
Bật verify chữ ký ở **admission** bằng Kyverno `verifyImages`, ưu tiên **keyless**
(GitHub Actions OIDC → Fulcio → Rekor) để không phải giữ khoá. Image
`ghcr.io/taitri2004/w10-app*` không có chữ ký khớp issuer/subject của repo sẽ bị
từ chối. Giữ sẵn bản key-based cho trường hợp offline.

## Phương án đã cân nhắc (Options considered)
1. Chỉ quét CVE ở CI, không verify ở cluster: nhanh nhưng không chặn được image
   lạ push thẳng vào registry rồi deploy.
2. Verify ở registry (admission của registry): tốt nhưng không phải registry nào
   cũng hỗ trợ, và vẫn không bảo vệ được khi đổi registry.
3. Verify ở admission cluster (chọn): chốt cuối cùng, độc lập registry, đúng
   nguyên tắc "không chạy cái gì không ký".

## Exception
Khi buộc chạy image chưa ký (vendor cũ, CVE chưa vá kịp), dùng `PolicyException`
giới hạn đúng workload, kèm `expiry` + `owner`. Kyverno KHÔNG tự hết hạn nên phải
rà bằng review/CI và xoá khi quá hạn. CVE miễn ở Trivy ghi trong `.trivyignore`
cũng theo nguyên tắc có hạn + có lý do.

## Hệ quả (Consequences)
- Tích cực: cluster chỉ chạy image có nguồn gốc rõ; supply chain tiến gần SLSA.
- Tiêu cực / đánh đổi: thêm webhook Kyverno vào đường admission (độ trễ + điểm
  phụ thuộc); exception cần kỷ luật rà soát, nếu quên xoá thì thành lỗ hổng.
