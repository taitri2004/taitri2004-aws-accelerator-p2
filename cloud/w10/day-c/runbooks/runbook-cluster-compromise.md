# Runbook: Pod/cluster nghi bị compromise — 5 phút đầu

- **Mức độ:** SEV-1
- **Chủ:** platform-team + security
- **Cập nhật:** 2026-06-17

> Theo IR playbook 6 bước: Detect → Triage → Contain → Eradicate → Recover →
> Post-mortem. 5 phút đầu = Triage + Contain. Ưu tiên CÁCH LY, giữ bằng chứng,
> KHÔNG xoá vội (mất dấu vết).

## Triệu chứng
- GuardDuty/Falco alert; pod chạy process lạ, traffic ra IP lạ, CPU/crypto-mining
  tăng đột biến, ServiceAccount token bị dùng bất thường.

## Tác động
- Tùy phạm vi: 1 pod → cả namespace → node → credential lan rộng.

## Các bước (5 phút đầu)
1. **Triage — xác định phạm vi**: pod nào, image gì, SA nào, node nào.
   ```bash
   kubectl get pod <p> -n <ns> -o wide
   kubectl get pod <p> -n <ns> -o jsonpath='{.spec.serviceAccountName}'
   ```
2. **Contain — cách ly pod, KHÔNG xoá** (xoá = mất bằng chứng + attacker biết):
   - Cắt mạng pod: gắn label cô lập + NetworkPolicy deny-all cho label đó.
   - Vô hiệu danh tính: thu hồi quyền của SA bị lạm dụng (xoá RoleBinding của nó).
   ```bash
   kubectl label pod <p> -n <ns> quarantine=true --overwrite
   kubectl apply -f <networkpolicy-deny-all-quarantine>
   ```
3. **Quyết định blast radius**: 1 pod compromised → cách ly POD trước. Nếu nghi
   node bị chiếm (escape) → cordon + drain node, snapshot để điều tra.
   ```bash
   kubectl cordon <node>     # không lên lịch pod mới
   ```
4. **Giữ bằng chứng**: dump log/process trước khi terminate; trên AWS: EBS
   snapshot + tách SG (pattern isolation học ở live T4).

## Leo thang
- SEV-1: báo ngay security owner + mentor, không tự xử một mình.

## Eradicate / Recover (sau khi đã contain)
- Rotate mọi secret pod đó chạm tới (ESO giúp rotate nhanh — xem
  `runbook-secret-rotation.md`). Xoá workload, deploy lại từ image đã ký.

## Sau sự cố
- Bắt buộc postmortem (`postmortem-template.md`): vào bằng đường nào, vì sao
  admission/RBAC không chặn, bịt thế nào.
