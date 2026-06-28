# Cách tôi hiểu dự án — TF3 Self-Heal Engine (góc nhìn CDO-02)

> Cá nhân nộp PM, EOD 2026-06-22. Mục đích: so khớp cách hiểu giữa các thành viên lúc 21:30.
> Người viết: <tên> · Vai: thành viên nhóm CDO-02 (platform/infra).
> Phạm vi: chỉ ghi phần việc của **nhóm CDO**. (Đổi tên file thành understanding-<tên-bạn>.md trước khi nộp.)

---

## 1. Một câu: dự án này là gì

Xây một **hệ thống tự động vận hành hạ tầng (auto-remediation / self-heal platform)** cho cụm Kubernetes: khi có sự cố thuộc loại đã biết, hệ thống **tự phát hiện → quyết định cách xử lý → tự thực thi lên cluster một cách an toàn → kiểm tra lại → nếu không sửa được thì báo người trực kèm báo cáo đầy đủ**. Đây **không phải web app FE+BE** — không có giao diện người dùng cuối; "người dùng" là on-call engineer và chính cái cluster.

## 2. Vấn đề của Client (vì sao họ cần)

- Client: VP Engineering, SaaS B2B, 200+ microservice trên EKS (us-east-1), ~120 tenant, peak ~8K RPS.
- Mỗi đêm on-call nhận 2-4 page, **80% là known patterns** lặp lại (pod OOMKilled, service stuck, queue backlog, cert hết hạn).
- Engineer thức 2h sáng chỉ để bấm "restart" → burnout đo được: eNPS 42→11, retention giảm 30% YoY.
- → Muốn tự động hóa 80% known patterns để engineer không bị đánh thức vì việc lặp lại.

## 3. Hệ thống làm gì — pipeline (và phần nào CDO sở hữu)

```
detect → match runbook → execute (có audit) → verify → escalate nếu fail
```

Nhóm CDO sở hữu **toàn bộ hạ tầng chạy pipeline này** + phần thực thi an toàn. Bước "quyết định nên làm action gì" gọi sang một **AI endpoint dùng chung của task force** (CDO tiêu thụ qua contract, không tự build phần đó).

Pipeline có **2 nhánh**, nhánh tự sửa là sản phẩm chính:
- **Nhánh thắng (mục tiêu ≥60%)**: tự phát hiện → tự sửa → verify OK → ghi audit → xong, không phiền ai.
- **Nhánh thua**: thử không được / lỗi lạ / chạm giới hạn an toàn → bỏ cuộc → gửi **Slack** kèm context bundle (logs, metrics, deploy history, các attempt đã thử).

Slack **không phải kết quả chính** — chỉ bật khi engine bó tay.

## 4. Nhóm CDO-02 build cái gì (phạm vi của tôi)

- **Sandbox EKS cluster** + node group + namespace structure.
- **Hạ tầng IaC (Terraform)**: VPC, EKS, IAM, S3 Object Lock (audit), Secrets Manager, observability.
- **Executor / glue code** nối luồng: `alert webhook → gọi AI endpoint → thực thi action lên cluster (có kiểm soát) → verify → ghi audit`.
- **5 safety guardrail** (phần này là giá trị cốt lõi của CDO): dry-run · blast-radius limit · verify post-act · auto-rollback · circuit breaker.
- **Multi-tenant isolation** (≥2 tenant) bằng RBAC + tách audit/scope.
- **CI/CD pipeline** + scan + canary deploy.
- **Observability stack** (metrics/logs/traces) + audit log query được (Athena hoặc UI).
- **E2E test**: bắn alert giả → chạy hết pipeline → audit log query được.

Phần "code" chủ yếu là **Terraform + K8s manifest + glue code** (Lambda / Step Functions / operator tùy angle), **không phải business logic kiểu app**.

## 5. Hard requirements nhóm CDO phải đảm bảo

> Lưu ý từ Q&A: **5 patterns trong brief chỉ là VÍ DỤ**, không cố định. Được tự chọn pattern nào value nhất (brainstorm GPT cũng được), NHƯNG phải chốt với team AI xem họ có cần pattern đó không.

- ≥3 patterns implemented+tested, ≥2 designed-only (paper + diagram + ADR).
- **Auto-resolve rate ≥60%** trên **≥10 scenarios**, test window **≥4h**.
- **Zero unsafe action** (không xóa namespace prod, không sửa IAM).
- Audit **tamper-evident** (S3 Object Lock), retention ≥90 ngày.
- **5 safety checkpoint MANDATORY** (mục §4).
- Multi-tenant ≥2 tenant + RBAC isolation (leak data giữa tenant = SEV1, cap tier).
- Escalation gửi đi kèm context bundle đầy đủ.

> 80% giá trị nhóm CDO nằm ở **an toàn + audit + isolation**, không phải ở việc "tự sửa được". Bot "lỗi là restart đại" sẽ trượt.

## 6. Out of scope (KHÔNG làm — tránh scope creep)

Multi-cluster federation · auto-discover pattern mới · cost-aware routing (→TF2) · cross-service root cause · production traffic (chỉ sandbox + synthetic) · real PagerDuty (Slack webhook đủ) · GitOps full · mTLS (JWT bearer đủ) · hash-chain crypto (Object Lock đủ) · predictive (→TF4).

## 7. Ba contracts — phần việc của nhóm CDO

CDO **review + push-back + ký** 3 contracts (ký T5 W11, sau đó FREEZE). Việc CDO phải làm theo contract:
1. **Telemetry Contract** — CDO **emit signals** cho engine (vd `pod_oom_event`, `api_latency_ms`); mọi payload bắt buộc có `tenant_id`, RFC3339 UTC, no PII.
2. **AI API Contract** — CDO **gọi** endpoint. Bắt buộc: lỗi `503` → CDO có **fallback rule-based**; `429` → exponential backoff.
3. **Deployment Contract** — CDO cấp: ServiceAccount + RBAC least-privilege (executor in-cluster, **KHÔNG cấp kubeconfig cho AI** — ADR-007), idempotency lock, audit S3 Object Lock; point tới endpoint dùng chung.

CDO có **endpoint thật (skeleton) từ T5 W11** để build mà không chờ logic hoàn chỉnh. **T3 W12 CDO phải gọi endpoint thật** (hết mock) — đây là mốc dependency thật.

## 8. Timeline & deliverable nhóm CDO phải nộp

- **W11**: bộ tài liệu *achievable* + base infra (VPC + EKS + observability) chạy được, lấy approve **T5 25/06**, ký 3 contracts.
- **W12**: build + integrate + chaos test. **8h sáng T5 02/07 code freeze**. Buổi chấm TF3: **13h30–15h15 T5 02/07**.
- Docs CDO: `01_requirements_analysis`, `02_infra_design`, `03_security_design`, `04_deployment_design`, `05_cost_analysis`, `07_test_eval_report`, `08_adrs` + `final-build/` + slides + demo + curveball responses + retrospective.

## 9. Cạnh tranh với CDO-01 — cách phân định (làm rõ từ Q&A)

- **Thắng/thua quyết ở T5 W12, KHÔNG phải tuần này.** T5 W11 chỉ approve tài liệu (về mặt khả thi). Sang W12 mỗi CDO làm **POC triển khai thật**, rồi **team AI mới chọn CDO nào phù hợp** dựa trên POC thực tế (chi phí vận hành, có đạt trên môi trường thật không) — không phải dựa trên doc đẹp. → **Execution W12 mới quyết.**
- **KHÔNG so sánh trực tiếp với CDO-01 trong doc.** Trainer chốt: bỏ §4 "Comparison với 2 nhóm cùng task force" trong `01_requirements_analysis.md` — vì các nhóm không được biết solution của nhau.
- Khác biệt vẫn nằm ở **HOW build platform**: angle kiến trúc (K8s-operator / Step-Functions orchestration / event-driven serverless / GitOps-driven) + execution quality (cost/tenant, p99 latency, recovery RTO, isolation strength, onboarding time, audit query UX, blast-radius enforcement).

- **Quan điểm cá nhân tôi**: <điền — bạn nghiêng angle nào, vì sao>

## 10. Logistics chốt trong buổi Q&A chiều nay (T2)

- **T5 (thứ 5) là hạn nộp toàn bộ tài liệu.** 3 mentor cùng review → khả thi thì ký + đóng dấu OK để triển khai POC; chưa ổn thì đá ngược về sửa.
- TF3 = 3 team (1 AI + 2 CDO). **2 CDO là 2 repo riêng.** Cả task force nên **thống nhất một version** để nộp.
- Hỏi thêm: ping mentor (anh Toàn / anh Khánh), **không trả lời ngay**, sau ~24h không phản hồi thì hỏi người khác.

## 11. Điều tôi CHƯA chắc / cần team thống nhất

<!-- Phần PM quan tâm nhất để so khớp. Thành thật. -->
- **Chọn pattern nào** (3 build + 2 design) + **chốt với AI** xem họ cần pattern đó không — chưa làm.
- **Angle kiến trúc** của nhóm mình (operator / orchestration / serverless...) — chưa lock, cần tránh trùng CDO-01.
- **Alert source** dùng nguồn nào là chính (Prometheus / CloudWatch / webhook) — chốt chung với AI.
- **Cấp quyền cho team AI** deploy engine lên hạ tầng mình thế nào cho bảo mật (account + connection) — CDO quyết.
- Các con số hard requirement (auto-resolve ≥60%, ≥10 scenarios, ≥4h) — giữ theo brief, recording không nói lại rõ; cần confirm khi làm POC.

## 12. Notes từ recording Q&A (T2 chiều — giải mã từ VTT, script nhiễu nên gist)

**Về data / metric / telemetry:**
- CDO lo thu thập **hardware/infra metric** (vd RAM pod): K8s → Prometheus, hạ tầng AWS → CloudWatch; rồi đẩy vào cho AI.
- Viết trong doc **cần data gì** → request; trainer cấp hoặc từ chối (không cấp PII kiểu số thẻ).
- **Eval dùng dữ liệu sandbox của chính mình (synthetic)**, không phải data thật client. Setup sandbox staging cluster.

**Về phối hợp AI ↔ CDO:**
- Làm **song song xuyên suốt 2 tuần**, không depend tuần tự. AI báo cần metric ABC → CDO cấp; engine AI chạy trên hạ tầng do CDO dựng.
- CDO **quản lý hạ tầng + cấp quyền truy cập** cho AI deploy engine (account + cách connect bảo mật) — CDO quyết.
- Contract AI có thể đổi nhưng **phải giới hạn thời gian**, không đổi đột ngột → họp liên tục.

**Về pattern / alert / escalation:**
- 5 patterns là **ví dụ**, tự chọn cái value nhất, chốt với AI.
- Alert source: chọn nguồn **value cao nhất, rõ nhất** (vd OOM qua Prometheus memory); mỗi alert nguồn khác nhau.
- Escalation **đừng chỉ đếm số lần retry** — pod crash nhiều nguyên nhân (memory/process/DB/node), dùng tín hiệu khác.

**Về quy trình / chấm:**
- **POC scope tối thiểu**, vừa đủ chứng minh giải pháp giải quyết vấn đề khách hàng.
- **T5 W11 = approve doc (khả thi). T5 W12 = AI chọn CDO tốt hơn dựa trên POC thật.**
- Nộp doc **incremental**, ưu tiên phần phụ thuộc team khác trước; đừng nộp một lần mấy trăm trang.
- **Bỏ §4 Comparison** trong `01_requirements_analysis.md` (không được biết solution nhau).
- 2 CDO = 2 repo riêng; cả task force thống nhất 1 version để nộp; ping mentor ~24h mới trả lời.
