# Postmortem: <Tên sự cố> — <ngày>

> Viết SAU sự cố để HỌC, không để đổ lỗi (blameless). Tập trung vào hệ thống &
> quy trình, không vào người. Mẫu theo Google SRE Workbook.

- **Trạng thái:** Draft / Final
- **Người viết:** <ai>
- **Mức độ:** SEV-?
- **Thời lượng:** từ <giờ phát hiện> đến <giờ hồi> (= <X> phút)

## Tóm tắt (1 đoạn)
<Chuyện gì xảy ra, ảnh hưởng ai, đã hồi chưa>

## Tác động
- <số user / request / tiền / SLO budget bị tiêu>

## Dòng thời gian (timeline)
| Thời gian | Sự kiện |
|---|---|
| 10:00 | alert fire |
| 10:05 | bắt đầu xử lý theo runbook |
| 10:30 | dịch vụ hồi |

## Nguyên nhân gốc (root cause)
<5 whys — đào tới nguyên nhân hệ thống, không dừng ở "ai đó bấm nhầm">

## Đã phát hiện / xử lý thế nào
- Phát hiện: <alert / user báo>
- Mitigate: <làm gì để hồi>

## Cái gì chạy tốt / cái gì tệ
- Tốt: <vd alert kịp, runbook có sẵn>
- Tệ: <vd thiếu dashboard, webhook failurePolicy=Fail không lường>

## Action items (có chủ + hạn)
| Việc | Chủ | Hạn | Loại |
|---|---|---|---|
| <vd: thêm liveness probe> | <ai> | <ngày> | phòng ngừa |
| <vd: đổi env -> volume mount> | <ai> | <ngày> | sửa gốc |
