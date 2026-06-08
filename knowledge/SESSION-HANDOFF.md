# SESSION HANDOFF — đọc đầu tiên ở session mới

> Cập nhật: 08/06/2026 (đầu W9). Mục đích: session mới (Claude) đọc file này là nắm
> toàn bộ context dự án, môi trường, quy ước, và bài học tái dùng — khỏi dò lại từ đầu.

---

## 1. Dự án & người dùng
- **Học viên:** taitri2004 — **thành viên team** (không phải PM/tech lead) trong Xbrain Accelerator Phase 2, track Cloud/DevOps.
- **Repo:** `C:\Users\ADMIN\Downloads\taitri2004-aws-accelerator-p2` → GitHub `taitri2004/taitri2004-aws-accelerator-p2`, branch `main`.
- **Nhịp tuần:** T2–T4 self-study (commit hằng ngày), T5–T6 onsite Đà Nẵng (lab + show-and-tell). Có Online Test T4 (scope D1+D2) và T6 (scope D3+Lab).
- **OS:** Windows, shell **PowerShell 5.1** (dùng tool PowerShell). Tiếng Việt.

## 2. AWS & môi trường
- **AWS account:** `749043157095`, user `admin`, region **`ap-southeast-1`** (CLI đã `aws configure`).
- **Tools đã cài (verified W8):** Terraform **v1.15.4**, AWS CLI + **session-manager-plugin**, Docker v29.4, kubectl **v1.34**, **minikube v1.38** (cluster local đã từng `minikube start`), Python + `pypdf`/`pdfplumber` (đọc PDF slide).
- **minikube W9:** announcement nói W9 build tiếp trên "cluster W8 (minikube)". Kiểm tra `minikube status`; nếu stop thì `minikube start`. Đừng `minikube delete`.

## 3. Quy ước đã thống nhất (GIỮ NGUYÊN cho W9)
- **Commit:** `[W9-D1] <topic ngắn>` (theo ngày). Push hằng ngày T2–T4.
- **Folder mỗi ngày** có thể chứa: `notes.md` (HV tự viết), `screenshots/`, code.
- **NOTES.md = riêng tư**, luôn **gitignore** (ghi chú/crib cá nhân, lý do thiết kế, câu trả lời mentor). **EVIDENCE_PACK.md = commit** (file gom bằng chứng, tách khỏi README).
- **README.md** chỉ đúng yêu cầu đề (vd lab: lệnh chạy + sơ đồ + giải thích) — không nhét ghi chú phụ.
- **.gitignore Terraform:** `**/.terraform/`, `*.tfstate*`, `*.tfvars` (giữ `*.tfvars.example`), `*.pem`, `NOTES.md`. **Commit** `.terraform.lock.hcl`.
- **Bí mật:** không hardcode/commit; dùng `sensitive`, tfvars (gitignore), `TF_VAR_`.
- **Luôn `destroy` sau khi lấy evidence** (EC2/RDS/ALB tính tiền). Apply → verify → screenshot → destroy.

## 4. ⚙️ PowerShell / môi trường — bẫy đã gặp (QUAN TRỌNG, tái dùng)
- **PATH cho tool mới cài** (minikube...) chưa có trong session: prepend
  `$env:Path = [Environment]::GetEnvironmentVariable("Path","Machine")+";"+[Environment]::GetEnvironmentVariable("Path","User")`.
- **Chạy AWS/terraform/cài đặt:** dùng `dangerouslyDisableSandbox: true` (cần network/credentials).
- **`curl` trong PS** = alias `Invoke-WebRequest` (không có `-s`). Lấy IP: `Invoke-RestMethod 'https://api.ipify.org'`. Gọi HTTP thật/đa connection: dùng **`curl.exe`**.
- **Ghi SSH PEM key:** PowerShell `>` tạo UTF-16 làm hỏng key. Dùng:
  `$k=((terraform output -raw ssh_private_key) -join "`n")+"`n"; [IO.File]::WriteAllText("$PWD\lab.pem",$k)` rồi `icacls lab.pem /inheritance:r /grant:r "$($env:USERNAME):(R)"`.
- **JSON cho `aws ssm send-command`:** viết ra file rồi `--parameters file://...` (tránh escape quote địa ngục).
- **`terraform plan` khi có `backend "s3"` mà bucket chưa tồn tại:** tạo file `zz_local_override.tf` = `terraform { backend "local" {} }` → `init -reconfigure` → plan ($0) → xoá override. (validate thì chỉ cần `init -backend=false`.)

## 5. 💡 Bài học kỹ thuật W8 — tái dùng cho W9
- **kind trên EC2:** dùng `extraPortMappings` (containerPort→hostPort 0.0.0.0) để lộ NodePort ra host cho ALB. minikube `--driver=docker` KHÔNG tự lộ.
- **cloud-init chạy root nhưng `$HOME` ≠ `/root`** → kind ghi kubeconfig sai chỗ. Fix: `export HOME=/root; export KUBECONFIG=/root/.kube/config` + `kind get kubeconfig --name lab > /root/.kube/config`.
- **ALB giữ keep-alive** → ghim mọi request vào 1 pod (load-balance không thấy). Fix: nginx `keepalive_timeout 0`.
- **Hiện pod name lên app** (chứng minh LB): initContainer đọc Downward API (`metadata.name`) + `sed` vào HTML.
- **Bảo mật vào EC2:** ưu tiên **SSM Session Manager** (IAM role `AmazonSSMManagedInstanceCore` + outbound 443), KHÔNG mở SSH/22. Lấy lệnh từ xa: `aws ssm send-command`.
- **Remote state lock:** Terraform 1.10+ dùng **`use_lockfile = true`** (file `.tflock` trên S3) thay DynamoDB. Mentor Minh dạy S3+DynamoDB (kinh điển) — biết cả 2, chọn use_lockfile cho gọn.
- **Remote state là bài toán con-gà-quả-trứng:** bootstrap (local state) tạo bucket TRƯỚC; destroy thì env trước, bootstrap sau. State bucket cần `force_destroy=true` mới teardown sạch (lab).
- **Provider thứ 2 chọn theo NHU CẦU THẬT**, không nhồi: đã đi tls→cloudinit→`random` (suffix tên unique). "Đúng nghĩa" nhất là kubernetes/helm nhưng cần 2-stage apply → mất 1-click.
- **Templatefile `.tftpl`:** escape `%{` thành `% {` (vd CSS `@keyframes 50%{`), tránh `${...}` của bash/JS (dùng `$VAR` không ngoặc hoặc `$${}`).

## 6. W8 đã làm xong (đã commit) — bản đồ
- `cloud/w8/day-a/` — Terraform: secure S3 bucket trên AWS (notes + evidence).
- `cloud/w8/day-b/` — K8s foundation + minikube + nginx deploy demo.
- `cloud/w8/day-c/` — Terraform: state + **modules** (`secure-bucket`) + best practices + **ADR**.
- `cloud/w8/lab/` — **Challenge "K8s on AWS 1-click"**: EC2 + kind + ALB + app (aws+random, SSM, keepalive=0, pod-name LB). README + EVIDENCE_PACK + NOTES(private) + slides/presentation.html.
- `cloud/w8/exercise/` — **Final project (deck Minh tr.37)**: VPC pub/priv + EC2 + RDS MySQL + S3, module + environments/dev, remote state S3 `use_lockfile`, bootstrap/. **Đã test apply thật (19 res) → destroy sạch.**
- `knowledge/` — `w8-foundation-iac-k8s.md` (kiến thức nền), `test1-terraform-cram.md`, `test2-k8s-cram.md` (ôn thi), PDF slide mentor.
- **Git:** tất cả W8 đã commit & push. Chỉ `announcement/W9_phase2_announcement_cloud.md` chưa track.

## 7. 📅 W9 — "Deliver Smartly" (GitOps + Observability + Canary)
**Bắt đầu T2 08/06.** Mục tiêu: cluster W8 → GitOps-managed (ArgoCD), có observability đo SLO + burn-rate alert, mọi deploy canary auto-abort khi metric tệ. **Không apply manifest tay nữa.**

| Ngày | Nội dung |
|---|---|
| **T2 08/06** | D1 **GitOps & CI/CD** — GitHub Actions plan-on-PR/apply-on-merge, ArgoCD vs Flux, app-of-apps, sync waves, rollback (`git revert` vs `kubectl rollout undo`) |
| **T3 09/06** | D2 **Observability** — OTel SDK+Collector, Prometheus+Grafana+Loki, SLO/SLI, multi-window burn rate (fast 1h×5m, slow 6h×30m) |
| **T4 10/06** | D3 **Canary** — Argo Rollouts, Rollout CRD, AnalysisTemplate + Prometheus, abort criteria · **15-17h LIVE Minh (Observability)** · **17-18h Test 1 (scope D1+D2)** |
| **T5 11/06** | Onsite — Lab "GitOps-ify W8 platform + observability + canary" (full day) |
| **T6 12/06** | Onsite — hoàn thiện Lab → show-and-tell 13h30 → **15-16h Test 2 (scope D3+Lab)** |

**Folder W9 cần tạo:**
```
cloud/w9/
  day-a/   # GitOps & CI/CD — .github/workflows/ + argocd/
  day-b/   # Observability — otel/ + dashboards/ + alert-rules/
  day-c/   # Canary — rollout/ + analysis-template/
  lab/     # GitOps-ify + bolt-on
  reflection.md
```
Commit: `[W9-D1] ...`. Tài liệu chính: ArgoCD, GitHub Actions, OpenTelemetry, Prometheus/Grafana/Loki, Google SRE (SLO + burn rate), Argo Rollouts, k6 (load test). Link đầy đủ trong `announcement/W9_phase2_announcement_cloud.md`.

## 8. ✅ TODO ngay cho session W9
1. Đọc kỹ `announcement/W9_phase2_announcement_cloud.md` (đã có sẵn) — xác nhận lịch + tài liệu.
2. (Nếu chưa) `git add announcement/W9_phase2_announcement_cloud.md` + commit.
3. Tạo cấu trúc `cloud/w9/{day-a,day-b,day-c,lab}` + `reflection.md`.
4. Hôm nay **T2 = D1 GitOps & CI/CD** → bắt đầu self-study + làm evidence day-a (giống nếp W8: notes tự viết + screenshots + commit cuối ngày).
5. Test 1 **T4 17h** scope **D1+D2** → có thể làm cram sheet như `test1/test2` khi tới gần.
6. Kiểm tra `minikube status` (W9 build trên cluster này).
7. Nhắc Jira: daily update + evidence dạng text/link khi Done (No trace = no work).
