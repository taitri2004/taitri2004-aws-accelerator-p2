# W8 — Foundation: IaC + Containers + Kubernetes

> Tài liệu tổng hợp kiến thức cốt lõi cho Week 8, Phase 2 (Cloud/DevOps Accelerator).
> Scope: **Terraform (IaC) → Docker (Containers) → Kubernetes (Orchestration trên minikube)**.
> Mục tiêu: đây là *hành trang nền* của một DevOps/CloudOps — hiểu **tại sao**, không chỉ **làm thế nào**.

---

## Mục lục

0. [Tư duy nền: DevOps/CloudOps là gì](#0-tư-duy-nền)
1. [Infrastructure as Code (IaC)](#1-infrastructure-as-code-iac)
2. [Terraform](#2-terraform)
3. [Docker & Containers](#3-docker--containers)
4. [Kubernetes](#4-kubernetes)
5. [minikube — K8s local cho W8](#5-minikube--k8s-local)
6. [Sợi chỉ đỏ: 3 layer ráp lại thế nào](#6-sợi-chỉ-đỏ)
7. [Checklist tự kiểm tra trước Test 1 & Test 2](#7-checklist-tự-kiểm-tra)
8. [Glossary](#8-glossary)

---

## 0. Tư duy nền

DevOps không phải một tool, mà là một **cách vận hành**: rút ngắn vòng lặp từ "viết code" → "chạy trên production an toàn" bằng cách **tự động hoá** và **biến mọi thứ thành code có thể review/version/rollback**.

Ba trụ cột W8 chạm vào:

| Layer | Câu hỏi nó trả lời | Tool W8 |
|---|---|---|
| **Provisioning** | Hạ tầng (máy, mạng, DB) ở đâu ra? | Terraform |
| **Packaging** | App + dependency đóng gói chạy giống nhau mọi nơi thế nào? | Docker |
| **Orchestration** | Hàng chục/trăm container chạy, tự heal, tự scale ra sao? | Kubernetes |

Nguyên tắc xuyên suốt cần thấm:
- **Declarative > Imperative**: mô tả *trạng thái mong muốn*, để tool tự tính cách đạt được. (Bạn nói "tôi muốn 3 bản sao chạy", không phải "khởi động bản 1, rồi bản 2, rồi bản 3".)
- **Idempotency**: chạy 1 lần hay 100 lần, kết quả cuối giống nhau. Đây là tính chất khiến automation an toàn.
- **Immutability**: không sửa server đang chạy; thay vào đó build artifact mới rồi thay thế. Giảm "configuration drift" và "snowflake servers".
- **Single source of truth**: trạng thái hệ thống nằm trong Git + state file, không nằm trong đầu một ông sysadmin.

---

## 1. Infrastructure as Code (IaC)

### 1.1 Vấn đề IaC giải quyết
Trước IaC, hạ tầng được dựng bằng tay (click console AWS, SSH gõ lệnh). Hậu quả:
- **Không lặp lại được**: môi trường dev/staging/prod lệch nhau → "works on my machine".
- **Không audit được**: ai đổi gì, khi nào, vì sao — không ai biết.
- **Snowflake servers**: mỗi server một kiểu, không server nào dựng lại được từ đầu.

IaC = mô tả hạ tầng bằng file text, đưa vào Git. Lợi ích: **version control, code review, rollback, tái lập, tự động hoá, tài liệu sống**.

### 1.2 Hai trường phái IaC
- **Declarative** (Terraform, CloudFormation, K8s manifests): khai báo *cái muốn có*. Tool tự so sánh hiện trạng ↔ mong muốn và tính ra việc cần làm. → Idempotent tự nhiên.
- **Imperative / procedural** (script bash, Ansible một phần): liệt kê *các bước* phải làm theo thứ tự. → Dễ viết ban đầu nhưng khó idempotent, khó suy luận trạng thái cuối.

### 1.3 Provisioning vs Configuration Management
- **Provisioning** (Terraform): tạo *ra* tài nguyên — VPC, EC2, RDS, K8s cluster.
- **Configuration management** (Ansible, Chef, Puppet): cấu hình *bên trong* máy đã có — cài package, sửa config file.
- Thực tế thường kết hợp: Terraform dựng máy → Ansible cấu hình. Nhưng xu hướng hiện đại là **immutable**: build image sẵn (Packer/Docker) thay vì config máy đang chạy.

---

## 2. Terraform

### 2.1 Bản chất
Terraform (HashiCorp) là công cụ provisioning **declarative, cloud-agnostic**. Bạn viết file `.tf` bằng ngôn ngữ **HCL** (HashiCorp Configuration Language), Terraform gọi API của provider (AWS, Azure, GCP, Kubernetes, Cloudflare...) để đưa hạ tầng về đúng trạng thái khai báo.

Điểm mấu chốt khiến Terraform khác script: nó **giữ một state file** ghi lại "tôi đang quản những resource nào", nhờ đó biết cần *tạo / sửa / xoá* gì ở lần chạy sau.

### 2.2 Core workflow — phải thuộc lòng

```
Write  →  terraform init  →  terraform plan  →  terraform apply  →  (terraform destroy)
```

| Lệnh | Làm gì | Khi nào dùng |
|---|---|---|
| `terraform init` | Tải provider plugin, khởi tạo backend, cài module. Chạy đầu tiên trong mỗi project / khi đổi provider. | Lần đầu, hoặc sau khi thêm provider/module |
| `terraform fmt` | Format code chuẩn HCL | Trước mỗi commit |
| `terraform validate` | Kiểm tra cú pháp + tính hợp lệ (không gọi API) | Trong CI, trước plan |
| `terraform plan` | **Dry-run**: so state ↔ config ↔ thực tế, in ra diff (`+` tạo, `~` sửa, `-` xoá). KHÔNG đổi gì. | Luôn luôn, trước apply |
| `terraform apply` | Thực thi plan, gọi API provider. Hỏi xác nhận (trừ khi `-auto-approve`) | Khi đã review plan |
| `terraform destroy` | Xoá toàn bộ resource đang quản | Dọn dẹp lab, tránh tốn tiền |

> **Quy tắc vàng:** không bao giờ `apply` mà chưa đọc kỹ `plan`. Đọc plan là cách học HCL và hiểu hệ thống nhanh nhất.

### 2.3 HCL — các block cốt lõi

```hcl
# 1. terraform block — cấu hình chính Terraform: version, providers, backend
terraform {
  required_version = ">= 1.5"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"        # pessimistic constraint: cho phép 5.x, không lên 6.0
    }
  }
  # backend "s3" { ... }        # nơi lưu state (xem 2.5)
}

# 2. provider block — credential & region cho 1 provider
provider "aws" {
  region = var.region
}

# 3. variable — input, làm code tái sử dụng
variable "instance_type" {
  type        = string
  default     = "t3.micro"
  description = "Loại EC2"
}

# 4. resource — đơn vị hạ tầng được tạo/quản (QUAN TRỌNG NHẤT)
resource "aws_instance" "web" {
  ami           = data.aws_ami.ubuntu.id
  instance_type = var.instance_type
  tags = { Name = "w8-web" }
}

# 5. data — đọc thông tin có sẵn (không tạo mới)
data "aws_ami" "ubuntu" {
  most_recent = true
  owners      = ["099720109477"]
  filter { name = "name"  values = ["ubuntu/images/*-22.04-*"] }
}

# 6. output — xuất giá trị ra sau apply (vd: IP, DNS)
output "web_ip" {
  value = aws_instance.web.public_ip
}

# 7. locals — biến nội bộ, tính toán dùng lại
locals {
  common_tags = { Project = "aws-accelerator-p2", ManagedBy = "terraform" }
}
```

**Phân biệt resource vs data:** `resource` = Terraform *sở hữu & quản lý vòng đời* (tạo/sửa/xoá). `data` = chỉ *đọc* thứ đã tồn tại để tham chiếu.

**Reference & dependency:** khi bạn viết `aws_instance.web.id` ở resource khác, Terraform tự suy ra **dependency graph** và tạo tài nguyên đúng thứ tự. Hầu hết phụ thuộc là *ngầm* (implicit); chỉ dùng `depends_on` khi phụ thuộc không thể hiện qua reference.

### 2.4 Kiểu dữ liệu & meta-arguments hay gặp
- **Types:** `string`, `number`, `bool`, `list(...)`, `set(...)`, `map(...)`, `object({...})`, `tuple([...])`.
- **`count`**: tạo N bản giống nhau → truy cập qua index `[0]`, `[1]`.
- **`for_each`**: tạo nhiều bản theo map/set → truy cập qua key. **Ưu tiên `for_each` hơn `count`** khi danh sách có thể thay đổi giữa chừng (count dùng index nên xoá phần tử giữa sẽ recreate nhầm).
- **`for` expression**: biến đổi list/map: `[for s in var.list : upper(s)]`.
- **`lifecycle`**: `create_before_destroy`, `prevent_destroy`, `ignore_changes`.
- **`dynamic` block**: sinh nested block lặp lại.
- **Conditional creation**: `count = var.enabled ? 1 : 0` — tạo resource có điều kiện.
- **`-target`** (escape hatch): `terraform apply -target=...` apply riêng 1 resource. Chỉ dùng khi debug/sửa chữa — *không* dùng thường xuyên trong quy trình bình thường.
- **Validation sớm** (mentor nhấn mạnh): `validation {}` block trong `variable` để chặn input sai; **`precondition` / `postcondition`** trong `lifecycle` để khẳng định giả định trước/sau khi tạo resource → bắt lỗi sớm thay vì hỏng giữa apply.

### 2.5 State — khái niệm sống còn
`terraform.tfstate` (JSON) là **bản đồ giữa config của bạn ↔ tài nguyên thật ngoài cloud**. Không có nó, Terraform không biết resource nào nó đang quản.

Những điều phải nhớ về state:
- **Chứa secret** (password, key đôi khi nằm trong state) → **không bao giờ commit lên Git**. Thêm vào `.gitignore`: `*.tfstate`, `*.tfstate.*`, `.terraform/`.
- **Remote backend** cho team: lưu state ở **S3** (AWS), hoặc Terraform Cloud, GCS, Azure Blob. Lý do: chia sẻ state + **state locking** chống 2 người apply cùng lúc gây hỏng.
- **State locking — lưu ý phiên bản (mentor Nghĩa dạy theo TF mới):** trước đây khoá state bằng **bảng DynamoDB** riêng. Từ **Terraform 1.10+** backend S3 hỗ trợ khoá **native qua `use_lockfile = true`** (tạo file `.tflock` ngay trên S3) → **không còn cần DynamoDB**. Nếu đọc tài liệu cũ thấy `dynamodb_table` thì biết đó là cách deprecated.
- **Đừng sửa state bằng tay.** Dùng lệnh chuyên dụng: `terraform state list`, `terraform state show`, `terraform state mv`, `terraform state rm`, `terraform import`. (`mv` đổi tên/di chuyển resource trong state; `rm` gỡ khỏi quản lý *không xoá* tài nguyên thật; `import` đưa tài nguyên có sẵn vào state.)
- **Drift**: ai đó sửa tay trên console → state lệch thực tế. `terraform plan` sẽ phát hiện và đề xuất đưa về đúng.

### 2.6 Modules — tái sử dụng
**Module** = một thư mục chứa các file `.tf` đóng gói lại để dùng lại (input qua `variable`, output qua `output`).
- **Root module**: thư mục bạn chạy `terraform` trong đó.
- **Child module**: gọi qua `module "x" { source = "./modules/vpc" ... }`. Source có thể là local path, Terraform Registry, Git.
- Triết lý: module nên có **giao diện rõ ràng** (ít input bắt buộc, output hữu ích), làm *một việc tốt* (vd module VPC, module EKS).
- **Terraform Registry** (registry.terraform.io): chợ module công khai — đừng phát minh lại VPC.

### 2.7 Best practices (mức production)
1. **Format & validate trong CI**: `fmt -check`, `validate`, `plan` tự động trên mỗi PR.
2. **Tách môi trường** dev/staging/prod: bằng workspace hoặc (tốt hơn) thư mục/backend riêng + biến.
3. **Pin version**: provider và module luôn ghi version constraint → tránh "tự dưng hôm nay khác".
4. **Không hardcode secret**: dùng biến + secret manager (AWS Secrets Manager, Vault), không nhét vào `.tf`. Đánh dấu `sensitive = true` để Terraform che giá trị trong output/plan. **TF 1.10/1.11+** thêm **`ephemeral`** (giá trị chỉ tồn tại lúc chạy, *không* ghi vào state) và **write-only arguments** → đây là cách hiện đại giữ secret hoàn toàn ra khỏi state file.
5. **Đặt tên & tag nhất quán**: `common_tags` qua `locals`, gắn `ManagedBy = terraform`.
6. **State remote + lock** ngay từ đầu với team.
7. **Small, composable modules** thay vì một file `.tf` khổng lồ.
8. **`plan` trước, review diff, rồi mới `apply`** — kỷ luật bất biến.

---

## 3. Docker & Containers

### 3.1 Container là gì (và không phải là gì)
**Container** = một process (hoặc nhóm process) chạy *cô lập* trên host, đóng gói cùng toàn bộ dependency (thư viện, runtime, file config). Cô lập nhờ tính năng nhân Linux:
- **namespaces** — cô lập *góc nhìn*: PID, network, mount, user... (container tưởng nó có hệ thống riêng).
- **cgroups** — giới hạn *tài nguyên*: CPU, RAM, I/O.

> **Container ≠ VM.** VM ảo hoá *phần cứng* và chạy nguyên một OS kernel riêng (nặng, vài GB, boot chậm). Container *chia sẻ kernel* của host, chỉ đóng gói userspace (nhẹ, vài MB–vài trăm MB, khởi động mili-giây). Đánh đổi: cô lập yếu hơn VM một chút.

### 3.2 Image vs Container
- **Image**: bản đóng gói *bất biến, chỉ đọc*, gồm nhiều **layer** xếp chồng (mỗi lệnh trong Dockerfile = 1 layer, được cache & chia sẻ giữa các image).
- **Container**: một *instance đang chạy* của image, có thêm một lớp ghi (writable layer) ở trên cùng.
- Analogy: **image = class, container = object**.
- **Registry**: nơi lưu & phân phối image — Docker Hub, Amazon ECR, GHCR. `docker pull` / `docker push`.
- **OCI Image Spec**: chuẩn mở định nghĩa format image → image không khoá cứng vào Docker, chạy được trên containerd, Podman, K8s...

### 3.3 Dockerfile — các chỉ thị cốt lõi

```dockerfile
FROM node:20-alpine          # base image (alpine = nhỏ gọn)
WORKDIR /app                 # thư mục làm việc
COPY package*.json ./        # copy trước để tận dụng layer cache
RUN npm ci --only=production # cài deps — tạo 1 layer
COPY . .                     # copy source còn lại
EXPOSE 3000                  # tài liệu hoá port (không tự mở)
USER node                    # chạy non-root (bảo mật)
ENTRYPOINT ["node"]          # lệnh cố định
CMD ["server.js"]            # tham số mặc định (ghi đè được)
```

Phải hiểu:
- **Layer caching**: Docker cache từng layer. Copy `package.json` + cài deps *trước* khi copy source → đổi code không phải cài lại deps. Thứ tự chỉ thị ảnh hưởng tốc độ build cực lớn.
- **`ENTRYPOINT` vs `CMD`**: ENTRYPOINT = lệnh chính (khó ghi đè); CMD = tham số mặc định (dễ ghi đè khi `docker run`). Thường kết hợp.
- **`RUN` vs `CMD` vs `ENTRYPOINT`**: RUN chạy *lúc build*; CMD/ENTRYPOINT chạy *lúc container start*.

### 3.4 Best practices viết image
1. **Multi-stage build**: stage build (có compiler, dev deps) tách khỏi stage runtime (chỉ artifact) → image nhỏ, ít lỗ hổng.
2. **Base image nhỏ**: `alpine`, `distroless`, `-slim`.
3. **`.dockerignore`**: loại `node_modules`, `.git`, secret khỏi build context.
4. **Chạy non-root** (`USER`): giảm rủi ro bảo mật.
5. **Một process chính / container**: container nên làm một việc.
6. **Không nhét secret vào image** (image bị pull ra là lộ); truyền qua env/secret lúc runtime.
7. **Pin tag cụ thể** (`node:20.11-alpine`), tránh `latest` mơ hồ.
8. **Layer ít & gộp `RUN`** hợp lý (vd `apt-get update && apt-get install && rm -rf /var/lib/apt/lists/*` trong cùng RUN).

### 3.5 Lệnh Docker hay dùng
```bash
docker build -t myapp:1.0 .          # build image từ Dockerfile
docker images                         # liệt kê image
docker run -d -p 8080:3000 myapp:1.0  # chạy, map host:container port, detached
docker ps            / docker ps -a   # container đang chạy / tất cả
docker logs -f <id>                   # xem log
docker exec -it <id> sh               # vào shell trong container
docker stop/rm <id>                   # dừng/xoá
docker volume / docker network        # quản lý storage & mạng
docker system prune                   # dọn rác
```
- **Volume**: dữ liệu *bền* nằm ngoài vòng đời container (DB data). Container ephemeral, volume persistent.
- **Port mapping** `-p host:container`: container có network namespace riêng, phải map ra ngoài.

---

## 4. Kubernetes

### 4.1 Tại sao cần orchestration
Một container thì `docker run` là đủ. Nhưng production cần: chạy *hàng trăm* container trên *nhiều máy*, **tự khởi động lại khi chết** (self-healing), **scale** theo tải, **rolling update** không downtime, **load balance**, **service discovery**, quản lý config/secret, lên lịch đặt container vào máy phù hợp. → Đó là việc của **Kubernetes (K8s)**, container orchestrator chuẩn de-facto (CNCF).

K8s là **declarative**: bạn nộp *desired state* (YAML manifest), **control loop** liên tục so sánh *actual ↔ desired* và tự hành động để khớp lại. Đây chính là lý do K8s tự heal.

### 4.2 Kiến trúc cluster

**Control plane (bộ não):**
- **kube-apiserver** — cổng vào duy nhất, mọi thứ nói chuyện qua REST API này.
- **etcd** — key-value store, lưu *toàn bộ trạng thái* cluster (source of truth).
- **kube-scheduler** — quyết định Pod chạy trên Node nào.
- **kube-controller-manager** — chạy các control loop (đảm bảo desired = actual).
- **cloud-controller-manager** — tích hợp với cloud provider (LB, volume...).

**Worker node (cơ bắp):**
- **kubelet** — agent trên mỗi node, đảm bảo container trong Pod chạy đúng.
- **kube-proxy** — quản network rule, hiện thực Service/load balancing.
- **container runtime** — containerd / CRI-O (Docker không còn là runtime trực tiếp trong K8s từ 1.24).

> Mental model: bạn nói chuyện với **API server**, ghi *mong muốn* vào **etcd**, **controllers + scheduler** biến mong muốn thành thực tế trên các **node** qua **kubelet**.

### 4.3 Workload objects — phân tầng quan trọng

| Object | Vai trò | Khi dùng |
|---|---|---|
| **Pod** | Đơn vị nhỏ nhất K8s deploy. 1 Pod = 1+ container *chung* network (cùng IP/port space) & storage. | Hiếm khi tạo tay; là thứ controller tạo ra |
| **ReplicaSet** | Đảm bảo luôn có đúng N bản Pod. | Thường do Deployment quản, ít dùng trực tiếp |
| **Deployment** | Quản ReplicaSet + **rolling update / rollback**. Workload stateless chuẩn. | App web/API stateless |
| **StatefulSet** | Pod có *danh tính ổn định* + storage riêng theo thứ tự. | DB, Kafka, hệ có state |
| **DaemonSet** | Chạy đúng 1 Pod trên *mỗi node*. | Agent log/monitor (Fluentd, node-exporter) |
| **Job / CronJob** | Chạy tới hoàn thành / theo lịch. | Batch, backup, migration |

> **Pod là ephemeral** — chết là mất, sinh lại với IP mới. Đừng bao giờ gọi Pod trực tiếp; luôn đi qua **Service**.

### 4.4 Networking & Service discovery

- **Service** — abstraction cung cấp **IP ổn định + DNS name** cho một nhóm Pod (chọn qua **label selector**), tự load-balance. Vì Pod IP đổi liên tục, Service là điểm tựa cố định.
  - **ClusterIP** (mặc định): chỉ truy cập *trong* cluster.
  - **NodePort**: mở 1 port trên mọi node → truy cập từ ngoài (dev/test). minikube hay dùng.
  - **LoadBalancer**: xin LB từ cloud provider (prod trên cloud).
  - **ExternalName**: ánh xạ tới DNS ngoài.
- **kube-dns / CoreDNS**: mỗi Service có DNS nội bộ `my-svc.my-namespace.svc.cluster.local` → service discovery tự động.
- **Ingress**: lớp L7 (HTTP/HTTPS) định tuyến theo host/path vào nhiều Service, kèm TLS. Cần **Ingress Controller** (nginx, traefik). minikube: `minikube addons enable ingress`.
- **NetworkPolicy**: firewall ở tầng Pod — khai báo Pod nào được nói chuyện với Pod nào. Mặc định K8s *cho phép hết*; NetworkPolicy để siết lại (zero-trust). Cần CNI hỗ trợ (Calico, Cilium).

### 4.5 Config & Secret
- **ConfigMap**: lưu config dạng key-value / file (non-sensitive). Inject vào Pod qua env var hoặc mount file.
- **Secret**: như ConfigMap nhưng cho dữ liệu nhạy cảm (password, token, cert). **Lưu ý: Secret mặc định chỉ base64-encode, KHÔNG mã hoá** — cần bật encryption-at-rest cho etcd + RBAC chặt + (prod) dùng external secret (Vault, Sealed Secrets, External Secrets Operator).
- Triết lý **12-factor**: tách config khỏi code → cùng một image chạy mọi môi trường, chỉ đổi ConfigMap/Secret.

### 4.6 Health checks — probes (rất hay hỏi)
kubelet kiểm tra sức khoẻ container qua 3 loại probe:
- **livenessProbe**: container còn *sống* không? Fail → kubelet **restart** container. (Phát hiện deadlock/treo.)
- **readinessProbe**: container đã *sẵn sàng nhận traffic* chưa? Fail → **gỡ Pod khỏi Service endpoints** (không gửi traffic) nhưng không restart. (Vd: đang warm-up, đang load cache.)
- **startupProbe**: cho app *khởi động chậm* — chặn liveness/readiness chạy cho tới khi app start xong (tránh bị giết oan lúc boot).

Probe có thể là HTTP GET, TCP socket, hoặc exec command. **Phân biệt liveness vs readiness là câu hỏi phỏng vấn kinh điển.**

### 4.7 Scaling & scheduling
- **Manual**: `kubectl scale deploy/app --replicas=5`.
- **HPA (Horizontal Pod Autoscaler)**: tự tăng/giảm số Pod theo CPU/memory/custom metric (cần metrics-server).
- **VPA**: chỉnh request/limit của Pod.
- **Cluster Autoscaler**: thêm/bớt *node* (trên cloud).
- **requests vs limits**:
  - `requests` = lượng tài nguyên *đảm bảo*, scheduler dùng để xếp Pod vào node.
  - `limits` = trần *tối đa*; vượt CPU → bị throttle, vượt memory → bị **OOMKilled**.
- **Lập lịch nâng cao**: `nodeSelector`, `affinity/anti-affinity`, `taints & tolerations` (đẩy/giữ Pod khỏi/vào node nhất định).

### 4.8 Storage
- **Volume**: gắn vào Pod, đời sống theo Pod (hoặc lâu hơn tuỳ loại).
- **PersistentVolume (PV)**: tài nguyên lưu trữ thật trong cluster (admin cấp hoặc dynamic).
- **PersistentVolumeClaim (PVC)**: Pod *xin* storage qua PVC; K8s khớp PVC ↔ PV.
- **StorageClass**: định nghĩa "loại" storage để cấp **động** (vd gp3 trên AWS). minikube có default StorageClass sẵn.

### 4.9 kubectl — lệnh sống còn
```bash
kubectl get pods/svc/deploy [-A] [-o wide]   # liệt kê (-A = mọi namespace)
kubectl describe pod <name>                  # chi tiết + events (debug số 1)
kubectl logs <pod> [-f] [-c <container>]     # xem log
kubectl exec -it <pod> -- sh                 # vào shell
kubectl apply -f manifest.yaml               # declarative: áp dụng/cập nhật
kubectl delete -f manifest.yaml              # xoá theo file
kubectl scale deploy/app --replicas=3        # scale
kubectl rollout status/undo deploy/app       # theo dõi/rollback rolling update
kubectl get events --sort-by=.lastTimestamp  # xem chuyện gì đang xảy ra
kubectl port-forward svc/app 8080:80         # forward port về máy local (debug)
kubectl config get-contexts / use-context    # đổi cluster/context
```
> **Declarative (`apply -f`) > imperative (`create`/`run`)** cho mọi thứ vào Git. Imperative chỉ để debug/thử nhanh.

### 4.10 Manifest YAML mẫu (Deployment + Service)
```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: web
spec:
  replicas: 3
  selector:
    matchLabels: { app: web }        # selector PHẢI khớp labels của template
  template:
    metadata:
      labels: { app: web }
    spec:
      containers:
        - name: web
          image: myapp:1.0
          ports: [{ containerPort: 3000 }]
          resources:
            requests: { cpu: "100m", memory: "128Mi" }
            limits:   { cpu: "500m", memory: "256Mi" }
          readinessProbe:
            httpGet: { path: /healthz, port: 3000 }
            initialDelaySeconds: 5
          livenessProbe:
            httpGet: { path: /healthz, port: 3000 }
            initialDelaySeconds: 10
---
apiVersion: v1
kind: Service
metadata:
  name: web
spec:
  type: ClusterIP
  selector: { app: web }             # Service tìm Pod qua label này
  ports:
    - port: 80
      targetPort: 3000
```
**Điểm chết người dễ sai:** `selector` của Service/Deployment phải **khớp `labels`** của Pod template. Sai label = Service không thấy Pod = "tôi deploy rồi mà không truy cập được".

---

## 5. minikube — K8s local

minikube dựng một **cluster K8s 1-node (hoặc multi-node)** ngay trên laptop để học/dev — không tốn tiền cloud.

```bash
minikube start --driver=docker        # khởi cluster (driver: docker/hyperkit/virtualbox)
minikube status                        # trạng thái
kubectl get nodes                      # thấy node "minikube"
minikube dashboard                     # UI web
minikube addons list / enable ingress  # bật addon (ingress, metrics-server...)
minikube service <svc> --url           # lấy URL truy cập Service (NodePort)
minikube image load myapp:1.0          # nạp image local vào cluster (KHÔNG cần push registry)
minikube tunnel                        # giả lập LoadBalancer trên local
minikube stop / delete                 # dừng / xoá cluster
```

**Bẫy thường gặp với minikube:**
- Build image bằng Docker host → minikube *không thấy*. Giải: `minikube image load <img>` **hoặc** `eval $(minikube docker-env)` rồi build trong context của minikube, **và** đặt `imagePullPolicy: IfNotPresent` để K8s không cố pull từ registry.
- `type: LoadBalancer` sẽ "pending" mãi trên local → dùng `minikube tunnel` hoặc đổi sang NodePort.

**Công cụ cài trước T5 (04/06):** Docker Desktop (hoặc Docker Engine trên Linux) + kubectl + minikube. Verify: `docker --version`, `kubectl version --client`, `minikube version`.

---

## 6. Sợi chỉ đỏ

3 layer của W8 không rời rạc — chúng là một pipeline:

```
[Terraform]  dựng hạ tầng (VPC, node, cluster K8s)        ← provisioning
     │
[Docker]     đóng gói app thành image bất biến             ← packaging
     │  (push lên registry: ECR/Docker Hub)
     │
[Kubernetes] kéo image về, chạy, scale, heal, expose        ← orchestration
```

Một dòng chảy CI/CD điển hình (sẽ gặp ở W9–W10 với GitOps):
1. Dev push code → CI **build Docker image** → push lên registry với tag = commit SHA.
2. Cập nhật manifest K8s (image tag mới) → commit vào repo config.
3. **GitOps controller (ArgoCD/Flux)** thấy repo đổi → `apply` lên cluster.
4. K8s **rolling update**: tạo Pod mới (readiness OK mới nhận traffic), gỡ Pod cũ → **zero-downtime**.
5. **Observability** (Prometheus/Grafana, W10) theo dõi; lỗi → **rollback** bằng Git revert.

Còn cluster đó nằm trên hạ tầng nào? → **Terraform** dựng nên (EKS/GKE, networking, IAM). Vòng tròn khép kín: *mọi thứ là code, mọi thay đổi qua Git, mọi trạng thái có thể tái lập.*

---

## 7. Checklist tự kiểm tra

### Trước **Test 1 (T3 02/06 — scope Terraform)**, tự trả lời được:
- [ ] IaC là gì? Declarative khác imperative chỗ nào? Idempotency nghĩa là gì?
- [ ] 4 lệnh core workflow làm gì? Vì sao luôn `plan` trước `apply`?
- [ ] Phân biệt `resource` vs `data`, `variable` vs `output` vs `locals`.
- [ ] State file là gì, vì sao không commit, vì sao cần remote backend + lock?
- [ ] `count` vs `for_each` — khi nào dùng cái nào và vì sao?
- [ ] Module là gì, input/output ra sao? Version constraint `~> 5.0` nghĩa là gì?
- [ ] Implicit vs explicit dependency (`depends_on`)?

### Trước **Test 2 (T6 05/06 — scope K8s + Lab)**, tự trả lời được:
- [ ] Container khác VM thế nào? namespaces vs cgroups?
- [ ] Image vs container vs registry? Layer caching tối ưu Dockerfile ra sao?
- [ ] Vẽ được kiến trúc cluster: control plane (apiserver/etcd/scheduler/controller) + node (kubelet/kube-proxy/runtime).
- [ ] Pod vs ReplicaSet vs Deployment vs StatefulSet vs DaemonSet — dùng khi nào?
- [ ] **liveness vs readiness vs startup probe** — khác nhau & hệ quả khi fail?
- [ ] Service các loại (ClusterIP/NodePort/LoadBalancer); vì sao không gọi Pod trực tiếp?
- [ ] ConfigMap vs Secret; vì sao Secret "không thực sự bí mật" mặc định?
- [ ] requests vs limits; OOMKilled khi nào? HPA scale dựa trên gì?
- [ ] PV vs PVC vs StorageClass?
- [ ] Bẫy image local trên minikube và cách xử lý?

---

## 8. Glossary

| Thuật ngữ | Nghĩa ngắn |
|---|---|
| **IaC** | Infrastructure as Code — quản hạ tầng bằng file text version-controlled |
| **Declarative** | Khai báo trạng thái mong muốn, tool tự đạt được |
| **Idempotent** | Chạy nhiều lần cho cùng kết quả |
| **Drift** | Thực tế lệch khỏi state/config do sửa tay |
| **HCL** | Ngôn ngữ cấu hình của Terraform |
| **State** | File map config ↔ tài nguyên thật của Terraform |
| **Backend** | Nơi lưu state (local/S3/Terraform Cloud) |
| **Module** | Gói Terraform tái sử dụng |
| **Provider** | Plugin Terraform nói chuyện với 1 API (AWS, K8s...) |
| **Image** | Bản đóng gói app bất biến (read-only, nhiều layer) |
| **Container** | Instance đang chạy của image |
| **Registry** | Kho lưu/phân phối image (ECR, Docker Hub) |
| **OCI** | Chuẩn mở cho image & runtime container |
| **Namespace (Linux)** | Cơ chế cô lập góc nhìn của container |
| **cgroup** | Cơ chế giới hạn tài nguyên container |
| **Pod** | Đơn vị deploy nhỏ nhất của K8s (1+ container) |
| **Deployment** | Controller quản Pod stateless + rolling update |
| **Service** | IP/DNS ổn định + load balance cho nhóm Pod |
| **Ingress** | Định tuyến HTTP L7 vào cluster |
| **ConfigMap / Secret** | Config / dữ liệu nhạy cảm tách khỏi image |
| **Probe** | Health check container (liveness/readiness/startup) |
| **HPA** | Tự scale số Pod theo metric |
| **PV / PVC** | Storage thật / yêu cầu storage |
| **etcd** | Key-value store lưu trạng thái cluster K8s |
| **kubelet** | Agent trên node đảm bảo Pod chạy đúng |
| **CNI** | Chuẩn plugin mạng cho K8s (Calico, Cilium) |
| **GitOps** | Git là nguồn chân lý, controller tự sync lên cluster |

---

### Nguồn học sâu thêm (từ announcement + chuẩn ngành)
- Terraform: [HashiCorp Tutorials](https://developer.hashicorp.com/terraform/tutorials) · *Terraform: Up & Running* (Brikman) · [Best Practices](https://www.terraform-best-practices.com)
- Docker: [Docker Docs](https://docs.docker.com) · [docker-curriculum.com](https://docker-curriculum.com) · *Docker Deep Dive* (Poulton)
- Kubernetes: [kubernetes.io/docs](https://kubernetes.io/docs) · [Basics interactive](https://kubernetes.io/docs/tutorials/kubernetes-basics) · *Kubernetes in Action* (Lukša) · [kubectl Cheat Sheet](https://kubernetes.io/docs/reference/kubectl/cheatsheet)
- minikube: [minikube.sigs.k8s.io](https://minikube.sigs.k8s.io/docs/start)
- Mentor Nghĩa: [Terraform from Basics to Production](https://kkloudtarus.net/en/blog/series/terraform-from-basics-to-production) · [Docker from Basics to Swarm](https://kkloudtarus.net/en/blog/series/docker-from-basics-to-swarm)

> *Học W8 đừng học thuộc lệnh — học **mental model**: declarative + desired state + control loop. Hiểu được nó, mọi tool (Terraform, K8s, ArgoCD ở W9–10) đều là biến thể của cùng một tư tưởng.*

---

## Phụ lục — Lộ trình series của mentor Nghĩa Huỳnh

> Đọc theo đúng thứ tự này để bám sát cách mentor dạy. Series Terraform dùng **Terraform 1.15 + AWS provider v6**, "mọi lệnh chạy thật trên AWS".

### Terraform from Basics to Production (20 phần — phần cốt lõi)
1. IaC & CLI basics — vì sao quản tay thất bại, vai trò Terraform
2. Provider, Resources & `init→plan→apply→destroy` — resource AWS đầu tiên, version pinning, "known after apply"
3. HCL fundamentals — block, data types, expressions, functions, `terraform{}`
4. **State file & drift detection** — so sánh 3 chiều (config ↔ state ↔ reality)
5. **Dependency graphs** — implicit vs explicit `depends_on`, `-target`
6. **Remote state trên S3 với `use_lockfile`** — versioning, encryption, *thay thế DynamoDB lock đã deprecated*
7. State ops — `import`, `mv`, `rm`
8. **Secrets management** — `sensitive`, `ephemeral`, write-only args (TF 1.10/1.11+)
9. Variables, Outputs, Locals & **validation** — precondition/postcondition
10. Data sources, functions & dynamic blocks
11. **`count` vs `for_each`** & conditionals — "index trap"
12. Viết module đầu tiên → ... → capstone production project

### Docker from Basics to Swarm (12 phần)
1. Docker là gì & vì sao dùng — so sánh VM, image/container/registry
2. Kiến trúc Docker — client, daemon, **containerd, runc**
3. **Cấu tạo container** — namespaces, cgroups, union filesystem
4. Cài & chạy container đầu tiên — lifecycle
5. Images & cơ chế layer — pull, tag, Docker Hub
6. Viết Dockerfile & **build cache** — vì sao đặt cài deps trước copy code
7. Volumes & bind mounts — lưu data bền
8. Networking — bridge, veth, port mapping
9. **Docker Compose** — multi-container
10. Tối ưu image — multi-stage build & security (non-root, secret)
11. Docker Swarm — cluster, manager/worker, Raft
12. Swarm: service, scale, rolling update, self-healing

> *Lưu ý cho Test 1 (Terraform):* các phần **4, 5, 6, 8, 11** của series Terraform ở trên đúng là những chỗ hay ra câu bẫy nhất (state, drift, locking mới, secret, `count` vs `for_each`).
