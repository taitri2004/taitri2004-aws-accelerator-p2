# Chaos test — chứng minh khả năng tự hồi

Nguyên tắc: có **giả thuyết**, có **steady-state metric** so trước/sau, **blast
radius nhỏ**, dừng được.

## Thí nghiệm 1 — xoá pod, service vẫn sống

- **Giả thuyết:** xoá 1 pod của Deployment ≥ 2 replica → ReplicaSet tạo lại,
  service không rớt request (steady-state: tỉ lệ 200 giữ nguyên).
- **Blast radius:** 1 pod, 1 namespace.

```powershell
.\cloud\w10\day-c\chaos\kill-pod.ps1 -Namespace platform-app -Selector app=web
```

Quan sát: pod mới `Running` trong vài giây; với GitOps thì ArgoCD self-heal kéo
về desired; với canary thì metric xấu sẽ auto-abort (W9).

## Thí nghiệm 2 — Chaos Mesh (công cụ chuẩn, tuỳ chọn)

Cần cài Chaos Mesh trước. `podchaos.yaml` xoá ngẫu nhiên 1 pod mỗi 30s trong 2
phút để kiểm tra hệ tự hồi liên tục:

```powershell
kubectl apply -f cloud/w10/day-c/chaos/podchaos.yaml
kubectl describe podchaos kill-web -n platform-app   # xem các lần inject
kubectl delete -f cloud/w10/day-c/chaos/podchaos.yaml  # dừng thí nghiệm
```

> Dừng ngay nếu steady-state vỡ (request bắt đầu 5xx) — đó chính là phát hiện
> cần sửa, không phải thất bại của bài test.
