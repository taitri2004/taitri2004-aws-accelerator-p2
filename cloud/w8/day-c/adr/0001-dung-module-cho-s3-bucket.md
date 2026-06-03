# ADR 0001 — Dùng module tái sử dụng cho S3 bucket

> ADR (Architecture Decision Record) = ghi lại MỘT quyết định kiến trúc:
> bối cảnh, lựa chọn, lý do, hệ quả. Mục đích: người sau (và chính mình)
> hiểu "vì sao hồi đó quyết định vậy".

- **Trạng thái:** Accepted
- **Ngày:** 2026-06-03
- **Người quyết định:** taitri2004

## Bối cảnh (Context)
Ở day-a mình viết bucket, versioning, encryption và public access block trực tiếp trong `main.tf`. Cách này ổn khi chỉ có một bucket, nhưng khi cần nhiều bucket như `data` và `logs`, việc copy-paste toàn bộ resource sẽ vi phạm DRY và dễ làm cấu hình bảo mật bị lệch giữa các bucket.

## Quyết định (Decision)
Đóng gói pattern "secure S3 bucket" thành module `./modules/secure-bucket`. Module expose input qua `bucket_name`, `enable_versioning`, `tags` và trả output `bucket_id`, `bucket_arn`. Root module có thể gọi lại module nhiều lần với input khác nhau.

## Phương án đã cân nhắc (Options considered)
1. Copy-paste resource cho từng bucket: đơn giản lúc đầu nhưng không DRY, khó giữ cấu hình nhất quán.
2. Dùng `for_each` trên resource ở root module: gọn hơn copy-paste, nhưng khó tái sử dụng ở project khác.
3. Tách module: tái sử dụng tốt hơn, có interface input/output rõ ràng và phù hợp khi pattern được dùng lại nhiều lần. Phương án này được chọn.

## Hệ quả (Consequences)
- Tích cực: giảm copy-paste, cấu hình bảo mật nhất quán, dễ gọi lại cho nhiều bucket, dễ mở rộng thêm option trong tương lai.
- Tiêu cực / đánh đổi: thêm một lớp trừu tượng, cần maintain interface module và cần đọc cả root module lẫn child module để hiểu toàn bộ resource được tạo.
