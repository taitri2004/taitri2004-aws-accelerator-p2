# Runbook: <Tên sự cố>

> Runbook = checklist hành động cho MỘT sự cố cụ thể, để người trực làm theo mà
> không phải nghĩ lại từ đầu lúc 3h sáng. Viết TRƯỚC sự cố. Khác postmortem
> (viết SAU để học).

- **Mức độ:** SEV-? (1 = mất dịch vụ toàn bộ … 4 = ảnh hưởng nhỏ)
- **Chủ:** <team/người>
- **Cập nhật:** <ngày>

## Triệu chứng (nhận ra khi nào)
- <alert nào fire / user báo gì / dashboard ra sao>

## Tác động (blast radius)
- <ai/cái gì bị ảnh hưởng>

## Cách phát hiện / chẩn đoán
```bash
# lệnh kiểm tra nhanh
```

## Các bước xử lý (theo thứ tự)
1. <bước 1 — an toàn trước, mitigate trước khi tìm root cause>
2. <bước 2>
3. <xác nhận đã hồi: lệnh/metric chứng minh>

## Leo thang (escalation)
- Sau <X phút> chưa hồi → báo <ai>.

## Sau sự cố
- Mở postmortem nếu SEV ≤ 2 (xem `postmortem-template.md`).
