# Việc cần làm cho AIO Context Request — brief cho team CDO-02

> Mục đích: giải thích dễ hiểu để cả team nắm AIO (nhóm AI) đang cần gì ở mình, vì sao, và ai làm gì.
> Deliverable thật đã gom sẵn ở [`platform-context-pack.md`](platform-context-pack.md) — file này là bản "giải thích + phân việc".

---

## 0. Hiểu trong 1 phút: vì sao AIO cần mình cung cấp mấy thứ này?

Hình dung đơn giản:
- **AIO = bác sĩ ra quyết định.** Họ nhìn triệu chứng → chẩn đoán → kê "nên làm gì" (restart, scale...).
- **CDO (mình) = bệnh viện + y tá thực thi.** Mình dựng phòng ốc (cluster), gắn máy đo (telemetry), và là người **thật sự ra tay** (execute action), ghi sổ (audit).

Bác sĩ **không thể kê đơn đúng nếu không biết bệnh viện có gì**: có những phòng nào (namespace), bệnh nhân nào (service), được phép dùng thuốc gì (allowed action), y tá được quyền làm gì (RBAC), máy nào đo được chỉ số nào (telemetry). → Đó chính là "platform context" AIO xin.

**Ranh giới đã chốt**: AIO chỉ **quyết định** (trả action plan), **KHÔNG tự đụng cluster, KHÔNG giữ kubeconfig**. Mình (CDO) mới **thực thi** qua ServiceAccount trong cluster. (Xem ADR-007.)

---

## 1. ⭐ 5 việc LÀM TRƯỚC (AIO ưu tiên — đủ 5 cái này là họ chốt được engine)

1. **Cluster topology** — bản đồ cluster: có service nào, tenant nằm namespace nào, service nào phụ thuộc service nào.
2. **Service catalog + tenant mapping** — danh sách service + namespace + tenant + mức quan trọng + action được phép.
3. **Telemetry schema + sample payload** — 5 tín hiệu mình gửi cho AIO, lấy từ đâu, mẫu JSON thật.
4. **Allowed action matrix + RBAC** — action nào được phép/cấm + giới hạn + quyền ServiceAccount.
5. **Incident injection scenarios** — cách mình tạo lỗi giả để diễn tập (≥10 kịch bản, ≥4h).

---

## 2. Bảng đầy đủ 12 việc (giải thích dễ hiểu + ai làm + trạng thái)

| # | Việc | Nói dễ hiểu: AIO cần cái này để... | Mình giao ai | Trạng thái |
|---|---|---|---|---|
| 1 | **Cluster topology** | biết action tác động tới đâu, service nào phụ thuộc nhau → tính blast-radius | Infra/EKS | ✅ có trong pack §1 (Online Boutique, 2 ns) |
| 2 | **Service catalog** | target đúng tên deployment thật, phân biệt service critical/non-critical | Infra/EKS | ✅ pack §2 |
| 3 | **Allowed action matrix** | biết được phép làm gì, cấm gì, giới hạn bao nhiêu → "zero unsafe action" | Safety/executor | ✅ pack §3 |
| 4 | **RBAC contract** | validate trước: action engine trả có execute nổi không (đủ quyền không) | Security | ✅ pack §4 (khớp Terraform) |
| 5 | **Telemetry schema + sample** | có đủ data để detect/decide/verify; xác nhận mình emit được 5 signal | Observability | ✅ pack §5 (signal generic, enrich namespace/deployment) |
| 6 | **Alert source format** | biết alert đến từ đâu (AlertManager/webhook) + mẫu alert | Observability | ⚠️ bổ sung mẫu alert payload |
| 7 | **Incident injection plan** | xây bộ test ≥10 scenario để đo auto-resolve rate | QA/executor | ✅ pack §6 (cần viết script thật W12) |
| 8 | **Pre-state snapshot format** | để rollback + audit (biết trạng thái trước khi sửa) | Executor | ✅ pack §7 |
| 9 | **Audit storage interface** | biết ghi/đọc audit ở đâu (S3 Object Lock + Athena) | Infra/Security | ✅ pack §8 |
| 10 | **Verification metric source** | xác định "đã khỏi bệnh thật chưa" (metric về normal trong 5p) | Observability/executor | ✅ pack §9 |
| 11 | **Rollback mechanism per action** | biết mỗi action hỏng thì lùi lại kiểu gì | Executor | ✅ pack §11 |
| 12 | **Network/auth gọi AI engine** | mình gọi engine qua đâu, xác thực kiểu gì | Infra/Security | ✅ pack §10 |

> Hầu hết đã có **đáp án design** trong `platform-context-pack.md`. Việc còn lại chủ yếu là: (a) bổ sung mẫu alert payload (#6), (b) **viết script inject lỗi thật** (#7) cho W12, (c) team review + chốt rồi gửi AIO.

---

## 3. Giải thích từng việc cho người chưa quen (đọc to cho team)

**1. Cluster topology** — "Vẽ bản đồ cluster". Online Boutique (~11 service) chạy trong 2 namespace tenant. Service nào gọi service nào (vd frontend → checkout → payment). AIO cần để biết: sửa 1 chỗ thì ảnh hưởng ai.

**2. Service catalog** — "Danh bạ service". Mỗi service: tên, namespace, tenant, mức quan trọng (critical/không), được phép action gì. AIO target đúng tên thật, không đoán mò.

**3. Allowed action matrix** — "Bảng luật". Được restart, scale (+3 pod, max 5), patch memory (+50%), rollout undo. CẤM: xóa namespace, sửa IAM. → đây là bằng chứng "zero unsafe action".

**4. RBAC contract** — "Thẻ ra vào của y tá". ServiceAccount executor chỉ được làm gì, trong namespace nào. AIO dùng để: nếu action cần quyền mình không có → engine escalate thay vì trả action chạy không nổi.

**5. Telemetry schema** — "Mấy cái máy đo gửi số gì". 5 tín hiệu: error rate, latency, memory/CPU, log lỗi, trace lỗi. Mình xác nhận emit được, lấy từ Istio/Prometheus, và **gắn thêm namespace + deployment** để AIO biết sửa cái gì.

**6. Alert source** — "Còi báo động kêu kiểu gì". Alert đến từ AlertManager qua webhook; mình gửi AIO 1 mẫu alert để họ biết format.

**7. Incident injection** — "Kịch bản diễn tập cháy". Cách tạo lỗi giả: ép OOM (set memory thấp), làm service treo, v.v. + tín hiệu kỳ vọng + cách dọn dẹp. Cần ≥10 kịch bản chạy ≥4h.

**8. Pre-state snapshot** — "Chụp ảnh trước khi mổ". Trước khi sửa, lưu lại trạng thái (replica, image, memory limit) để lỡ sửa hỏng thì khôi phục.

**9. Audit storage** — "Sổ ghi chép không tẩy xóa được". Mọi bước ghi vào S3 Object Lock (90 ngày, không sửa được), query bằng Athena. Cho SOC2 + cho panel kiểm tra.

**10. Verification source** — "Kiểm tra bệnh nhân khỏe lại thật chưa". Sau khi sửa, đo lại metric trong cửa sổ 5 phút; metric về bình thường + ổn định mới tính "khỏi". Không phải "chạy lệnh xong là xong".

**11. Rollback per action** — "Cách lùi lại từng loại". Scale → trả replica cũ; patch memory → trả limit cũ; rollout → undo về revision trước.

**12. Network/auth** — "Đường dây + mật khẩu gọi bác sĩ". Gọi engine qua endpoint nội bộ `ai-engine.tf-3.internal`, xác thực IAM SigV4 + header tenant.

---

## 4. Phối hợp & deadline

- **Đáp án đã gom ở [`platform-context-pack.md`](platform-context-pack.md)** → team review file đó, ai phụ trách phần nào thì verify lại phần đó.
- **Bổ sung còn thiếu**: mẫu alert payload (#6) + script inject lỗi (#7, để W12).
- **Gửi AIO sớm** — contract FREEZE T5; mentor/AIO phản hồi chậm (~24h), đừng để sát giờ.
- **4 điểm cần AIO chốt lại** (đã ghi cuối pack): tên signal canonical, format topology graph, ai ghi audit, execute-fail xử lý sao.

---

## 5. Tóm 1 câu cho team
> AIO cần "bản đồ + luật chơi + máy đo" của cluster mình để họ ra quyết định đúng. 90% đã trả lời sẵn trong `platform-context-pack.md`; việc của team là **review, bổ sung mẫu alert + script inject lỗi, rồi gửi sớm trước freeze**.
