# Test 1 Cram Sheet — 30 challenge HCL (luyện gõ nhanh < 90s)

> Bài thi: viết HCL → bấm `terraform apply` → chấm bằng test case. Có Docs nhúng.
> Tiến trình challenge: provider → resource → variable → data type → expression → module.
> Mục tiêu file này: gõ được TỪ TRÍ NHỚ các pattern dưới đây, khỏi tốn giây tra docs.
> CÁCH DÙNG: che cột phải, tự gõ lại trong day-a/day-c local, `terraform validate` để check.

---

## 1. PROVIDER
```hcl
provider "aws" {
  region = "ap-southeast-1"
}
```
Pin version (nếu đề yêu cầu terraform block):
```hcl
terraform {
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 6.0"
    }
  }
}
```
Nhớ: `~> 6.0` = cho 6.x, chặn 7.0. `>= 1.5` = từ 1.5 trở lên.

## 2. RESOURCE (luôn 2 label: type + local name)
```hcl
resource "aws_instance" "web" {
  ami           = "ami-0c02fb55956c7d316"
  instance_type = "t2.micro"
  tags = {
    Name = "web-server"
  }
}
```
Tham chiếu resource khác: `aws_instance.web.id` (implicit dependency).

## 3. VARIABLE
```hcl
variable "instance_type" {
  type        = string
  default     = "t2.micro"
  description = "EC2 instance type"
}
```
Có validation:
```hcl
variable "env" {
  type = string
  validation {
    condition     = contains(["dev", "prod"], var.env)
    error_message = "env phải là dev hoặc prod."
  }
}
```
Secret: thêm `sensitive = true`. Bắt buộc nhập: bỏ `default`.
Dùng biến: `var.instance_type`.

## 4. OUTPUT & LOCALS
```hcl
output "instance_ip" {
  value       = aws_instance.web.public_ip
  description = "Public IP"
  sensitive   = false
}

locals {
  name_prefix = "${var.env}-${var.project}"
  common_tags = { ManagedBy = "terraform" }
}
```
Dùng local: `local.name_prefix`.

## 5. DATA TYPES (nhớ cú pháp literal)
```hcl
# string  -> "hello"
# number  -> 42      3.14
# bool    -> true    false
# list    -> ["a", "b", "c"]
# map     -> { key = "value", port = "80" }
# object  -> { name = "x", port = 80 }
# tuple   -> ["a", 1, true]
```
Khai báo type phức:
```hcl
variable "subnets"  { type = list(string) }
variable "settings" { type = map(string) }
variable "server" {
  type = object({
    name = string
    port = number
  })
}
```
Truy cập: list `var.subnets[0]`, map `var.settings["key"]`, object `var.server.port`.

## 6. DATA SOURCE (READ, không tạo)
```hcl
data "aws_ami" "amazon_linux" {
  most_recent = true
  owners      = ["amazon"]
  filter {
    name   = "name"
    values = ["amzn2-ami-hvm-*-x86_64-gp2"]
  }
}
# dùng: data.aws_ami.amazon_linux.id
```
Hữu ích: `data "aws_caller_identity" "current" {}` → `.account_id`.

## 7. EXPRESSIONS / META-ARGUMENTS

**count** (tạo N bản, truy cập index):
```hcl
resource "aws_instance" "web" {
  count         = 3
  instance_type = "t2.micro"
  tags = { Name = "web-${count.index}" }
}
# tham chiếu: aws_instance.web[0].id
```

**for_each** (theo set/map, truy cập key):
```hcl
resource "aws_instance" "web" {
  for_each      = toset(["dev", "prod"])
  instance_type = "t2.micro"
  tags = { Name = each.key }     # each.key / each.value
}
# tham chiếu: aws_instance.web["dev"].id
```

**conditional** (ternary):
```hcl
instance_type = var.is_prod ? "t3.large" : "t2.micro"
count         = var.enabled ? 1 : 0
```

**for expression** (biến đổi list/map):
```hcl
[for s in var.names : upper(s)]                  # -> list
{ for s in var.names : s => length(s) }          # -> map
[for s in var.names : s if s != ""]              # có filter
```

**string interpolation**: `"${var.env}-app"`

## 8. FUNCTIONS hay dùng (gõ nhớ)
```
length(list)            element(list, idx)      lookup(map, key, default)
contains(list, val)     keys(map)   values(map)
join(",", list)         split(",", str)
toset(list)  tolist(set)  tomap(...)  tostring(x)  tonumber(x)
upper/lower/title(str)   trimspace(str)   replace(s, old, new)
merge(map1, map2)        concat(l1, l2)
cidrsubnet(prefix, newbits, netnum)
format("web-%d", n)      coalesce(a, b, c)
file("path")             jsonencode(x)   can(...)   try(...)
```

## 9. MODULE (gọi module)
```hcl
module "vpc" {
  source     = "./modules/vpc"
  cidr_block = "10.0.0.0/16"
  env        = "prod"
}
# dùng output module: module.vpc.vpc_id
```
Trong module: input = `variable`, expose = `output`. Cấu trúc: main.tf / variables.tf / outputs.tf.

---

## ⚡ MẸO LÀM BÀI
- **Câu 1-15 (provider→expression)**: gõ thẳng từ trí nhớ, không mở docs → bank thời gian.
- **Bí tên argument** → mở Docs, search đúng tên resource (vd "aws_s3_bucket"), kéo tới "Argument Reference" hoặc "Example Usage", copy.
- **KHÔNG bấm Gợi ý** (−25đ). Docs là đủ.
- Đọc đề kỹ, chắc mới `apply` (sai >3 lần mới bị trừ → còn 3 lần thử, đừng phí).
- Lỗi hay gặp: thiếu dấu `=`, quên ngoặc kép string, resource thiếu 1 label, dùng `var.x` mà chưa khai `variable`.
- `terraform fmt` không cần lúc thi (chấm bằng test case, không chấm format).

## 🧪 TỰ LUYỆN trước giờ G
Mở `cloud/w8/day-c` local, thử gõ lại từng pattern trên rồi `terraform validate`.
Bấm giờ: ép mình mỗi pattern < 60s.

---

# 📝 ĐỀ THỬ (20 câu) — tự làm rồi mới xem đáp án

> Cách luyện: đọc đề → che phần "Giải" → tự gõ → bấm giờ < 90s → mở ra đối chiếu.
> Độ khó tăng dần đúng theo tiến trình thi: provider → resource → variable → type → expression → module.

## NHÓM A — Provider & Resource

**Câu 1.** Cấu hình provider AWS chạy ở region Singapore (`ap-southeast-1`).
<details><summary>Giải</summary>

```hcl
provider "aws" {
  region = "ap-southeast-1"
}
```
</details>

**Câu 2.** Khai báo `terraform` block yêu cầu provider `aws` của hashicorp, version cho phép 6.x nhưng không lên 7.0.
<details><summary>Giải</summary>

```hcl
terraform {
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 6.0"
    }
  }
}
```
Nhớ: `~> 6.0` ⇒ `>= 6.0, < 7.0`.
</details>

**Câu 3.** Tạo resource `aws_s3_bucket` tên local là `data`, bucket = `"my-app-data-123"`, gắn tag `Environment = "dev"`.
<details><summary>Giải</summary>

```hcl
resource "aws_s3_bucket" "data" {
  bucket = "my-app-data-123"
  tags = {
    Environment = "dev"
  }
}
```
Nhớ: resource luôn **2 label** — type `"aws_s3_bucket"` + name `"data"`.
</details>

**Câu 4.** Tạo `random_pet` tên `name`, `length = 2`, `separator = "-"`.
<details><summary>Giải</summary>

```hcl
resource "random_pet" "name" {
  length    = 2
  separator = "-"
}
```
</details>

## NHÓM B — Variable, Output, Locals

**Câu 5.** Khai báo biến `instance_type` kiểu string, mặc định `"t2.micro"`, có description.
<details><summary>Giải</summary>

```hcl
variable "instance_type" {
  type        = string
  default     = "t2.micro"
  description = "EC2 instance type"
}
```
</details>

**Câu 6.** Biến `environment` (string) chỉ nhận `"dev"`, `"staging"`, `"prod"` — nếu khác báo lỗi.
<details><summary>Giải</summary>

```hcl
variable "environment" {
  type = string
  validation {
    condition     = contains(["dev", "staging", "prod"], var.environment)
    error_message = "environment phải là dev, staging hoặc prod."
  }
}
```
</details>

**Câu 7.** Biến `db_password` kiểu string, không có default, ẩn giá trị khỏi output.
<details><summary>Giải</summary>

```hcl
variable "db_password" {
  type      = string
  sensitive = true
}
```
Không `default` ⇒ bắt buộc nhập. `sensitive = true` ⇒ che trong plan/output.
</details>

**Câu 8.** Tạo `locals` có `name_prefix` ghép từ `var.project` và `var.environment` (dạng `project-env`).
<details><summary>Giải</summary>

```hcl
locals {
  name_prefix = "${var.project}-${var.environment}"
}
```
Dùng sau: `local.name_prefix`.
</details>

**Câu 9.** Output `bucket_arn` = ARN của `aws_s3_bucket.data` ở câu 3, kèm description.
<details><summary>Giải</summary>

```hcl
output "bucket_arn" {
  value       = aws_s3_bucket.data.arn
  description = "ARN của bucket data"
}
```
</details>

## NHÓM C — Data types

**Câu 10.** Biến `availability_zones` là **list of string**, mặc định 2 AZ Singapore.
<details><summary>Giải</summary>

```hcl
variable "availability_zones" {
  type    = list(string)
  default = ["ap-southeast-1a", "ap-southeast-1b"]
}
```
</details>

**Câu 11.** Biến `tags` kiểu **map(string)**, mặc định rỗng.
<details><summary>Giải</summary>

```hcl
variable "tags" {
  type    = map(string)
  default = {}
}
```
</details>

**Câu 12.** Biến `server` kiểu **object** gồm `name` (string) và `port` (number).
<details><summary>Giải</summary>

```hcl
variable "server" {
  type = object({
    name = string
    port = number
  })
}
```
Truy cập: `var.server.name`, `var.server.port`.
</details>

## NHÓM D — Expressions / meta-arguments

**Câu 13.** Tạo 3 bucket `aws_s3_bucket` tên `web`, đặt tên lần lượt `web-0`, `web-1`, `web-2` bằng **count**.
<details><summary>Giải</summary>

```hcl
resource "aws_s3_bucket" "web" {
  count  = 3
  bucket = "web-${count.index}"
}
```
Tham chiếu: `aws_s3_bucket.web[0].id`.
</details>

**Câu 14.** Tạo bucket cho mỗi môi trường trong `["dev", "prod"]` bằng **for_each**, bucket name = tên môi trường.
<details><summary>Giải</summary>

```hcl
resource "aws_s3_bucket" "env" {
  for_each = toset(["dev", "prod"])
  bucket   = each.key
}
```
`each.key` = `each.value` với set. Tham chiếu: `aws_s3_bucket.env["dev"].id`.
</details>

**Câu 15.** Gán `instance_type` = `"t3.large"` nếu `var.is_prod` true, ngược lại `"t2.micro"` (**conditional**).
<details><summary>Giải</summary>

```hcl
instance_type = var.is_prod ? "t3.large" : "t2.micro"
```
</details>

**Câu 16.** Chỉ tạo resource khi `var.enabled` = true (**conditional + count**).
<details><summary>Giải</summary>

```hcl
resource "aws_s3_bucket" "optional" {
  count  = var.enabled ? 1 : 0
  bucket = "optional-bucket"
}
```
</details>

**Câu 17.** Cho `var.names = ["a", "b"]`. Dùng **for expression** tạo list viết HOA.
<details><summary>Giải</summary>

```hcl
output "upper_names" {
  value = [for n in var.names : upper(n)]
}
```
Kết quả: `["A", "B"]`.
</details>

**Câu 18.** Cho `var.names`. Tạo **map** `{ tên => độ dài tên }` bằng for expression.
<details><summary>Giải</summary>

```hcl
output "name_lengths" {
  value = { for n in var.names : n => length(n) }
}
```
</details>

## NHÓM E — Data source & Module

**Câu 19.** Đọc AMI Amazon Linux 2 mới nhất (owner `amazon`, filter name `amzn2-ami-hvm-*-x86_64-gp2`) rồi dùng cho `aws_instance`.
<details><summary>Giải</summary>

```hcl
data "aws_ami" "amazon_linux" {
  most_recent = true
  owners      = ["amazon"]
  filter {
    name   = "name"
    values = ["amzn2-ami-hvm-*-x86_64-gp2"]
  }
}

resource "aws_instance" "web" {
  ami           = data.aws_ami.amazon_linux.id
  instance_type = "t2.micro"
}
```
Nhớ: data source **đọc**, không tạo. Tham chiếu `data.<type>.<name>.<attr>`.
</details>

**Câu 20.** Gọi module local ở `./modules/vpc`, truyền `cidr_block = "10.0.0.0/16"` và `env = "prod"`; rồi output `vpc_id` lấy từ output `vpc_id` của module.
<details><summary>Giải</summary>

```hcl
module "vpc" {
  source     = "./modules/vpc"
  cidr_block = "10.0.0.0/16"
  env        = "prod"
}

output "vpc_id" {
  value = module.vpc.vpc_id
}
```
Tham chiếu output module: `module.<tên>.<output>`.
</details>

---

## ✅ Tự chấm
Làm xong 20 câu trong **< 25 phút** + không tra docs quá 3 câu ⇒ bạn sẵn sàng cho 30 challenge chiều nay.
Câu nào ngắc ngứ → quay lại phần cram tương ứng (mục 1-9) học lại pattern đó.
