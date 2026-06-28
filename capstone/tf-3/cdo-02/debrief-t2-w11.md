# Debrief Client Interview — TF3 Self-Heal Engine · CDO-02

> Gửi mentor confirm **trước EOD T2 W11**. Mục đích: chốt cách hiểu brief, lộ giả định sai sớm để tránh rework T3-T4.
> Cách dùng: điền `<...>`, xóa dòng không dùng. Câu nào Client CHƯA trả lời → ghi vào §3 (giả định) + §4 (open question), đừng để trống lặng lẽ.

- **Buổi**: Q&A with Trainers — AIO-04 + CDO-01 + CDO-02
- **Ngày/giờ**: 2026-06-22, 14:30–15:00
- **Người ghi**: <tên> (CDO-02)
- **Trainer/Client đóng vai**: <tên mentor>

---

## 1. Tôi hiểu vấn đề Client là...

<!-- 2-3 câu restate bằng lời mình. Không copy brief. -->
- <vd: On-call burnout vì 80% alert là known patterns, cần auto-remediate để engineer không bị đánh thức 2h sáng; ưu tiên AN TOÀN + AUDIT hơn là cover hết mọi lỗi.>

## 2. Tôi hiểu các điểm Client chốt là... (chỉ những gì CHỈ Client quyết được)

> Đây là 6 câu mình **không tự quyết được** — phụ thuộc định nghĩa thành công / ưu tiên business / khẩu vị rủi ro / môi trường / compliance của Client.
> (Auth pattern, idempotency, rollback method, isolation pattern, latency budget... → mình tự chốt + ghi ADR, KHÔNG hỏi ở đây.)

| # | Điểm cần Client chốt | Vì sao chỉ Client quyết được | Tôi hiểu Client trả lời là... |
|---|---|---|---|
| 1 | **Định nghĩa "auto-resolved"** — action execute success, hay metric về normal sau verify? | Đây là success criteria — quyết công thức auto-resolve rate ≥60% | <...> |
| 2 | **5 patterns ưu tiên** + xếp hạng business impact | Ưu tiên business là kiến thức của Client, không tự đoán | <...> |
| 3 | **Blast-radius giới hạn cứng** (max % cluster / max N pod tự động đụng vào) | Khẩu vị rủi ro của Client — họ chịu được auto-act tới đâu | <...> |
| 4 | **Sandbox + alert source**: cluster spec (K8s ver, node), alert đến từ đâu (Prometheus/CloudWatch/webhook), **ai inject incident** | Fact về môi trường được cấp — không tự bịa được | <...> |
| 5 | **Escalation policy**: thử mấy lần mới bỏ cuộc (1/3/per-pattern) + response SLA | Chính sách vận hành on-call của Client | <...> |
| 6 | **Audit/compliance**: SOC2 control cụ thể nào phải chứng minh (CC6.1/CC7.2/CC8.1) + ai cần quyền query audit | Yêu cầu compliance — Client/Compliance owns | <...> |

## 3. Giả định tôi đang giữ (Client CHƯA confirm rõ)

<!-- Chỗ Client trả lời mơ hồ / chưa kịp hỏi → mình tạm assume để build, cần mentor xác nhận. -->
- **Giả định 1**: <vd: Slack webhook đủ cho escalation, không cần PagerDuty thật> — *impact nếu sai: <...>*
- **Giả định 2**: <vd: single EKS cluster us-east-1, không multi-cluster> — *impact nếu sai: <...>*
- **Giả định 3**: <...>

## 4. Open questions còn lại (hỏi daily Q&A 15-16h / ping mentor riêng)

- [ ] Q1: <câu chưa kịp hỏi trong 30 phút>
- [ ] Q2: <...>

## 5. Hệ quả tới hướng đi CDO-02 (nội bộ, chưa lock — đừng lộ với CDO-01)

- **Differentiation angle đang cân nhắc**: <K8s-operator-native / Step-Functions orchestration / event-driven serverless / ...>
- **Trục cạnh tranh với CDO-01 dự kiến**: <cost / reliability / ops simplicity / latency / isolation strength>
- **Nghe được từ CDO-01 trong buổi**: <họ nghiêng về angle gì → mình né hướng nào>

## 6. Xác nhận từ mentor

> Anh/chị xem giúp em §2 + §3 có chỗ nào em hiểu sai brief không ạ? Đặc biệt giả định §3 — nếu sai em re-design sớm trước khi build T6.

- **Mentor phản hồi**: <điền sau khi nhận reply>
- **Điều chỉnh sau confirm**: <...>
```
