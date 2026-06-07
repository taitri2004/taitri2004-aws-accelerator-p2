# Test 2 Cram Sheet — Kubernetes YAML (luyện gõ nhanh < 120s)

> Bài thi: viết YAML manifest → `kubectl apply` → hệ thống verify **state thật** trên cluster
> (giống CKA). Áp vào **namespace riêng của bạn**. Có Kubernetes Docs nhúng sẵn.
> Scope: **Pods · Deployments/replicas · Services · ConfigMap · Labels · Resources**.
> CÁCH DÙNG: che cột phải, tự gõ, `kubectl apply -f` + `kubectl get` để check.

---

## 🎯 Đọc luật → chiến thuật

| Luật | Hệ quả chiến thuật |
|---|---|
| **120 giây/câu**, vượt −5đ/10s | Dùng **imperative generator** (`--dry-run=client -o yaml`) sinh khung rồi sửa → nhanh hơn gõ tay nhiều |
| **Sai >3 lần** −15đ/lần | `kubectl apply --dry-run=server -f` để check trước khi apply thật. Đọc lỗi kỹ. |
| **Gợi ý** −25đ | Dùng **nút Docs / `kubectl explain`** (miễn phí) thay hint |
| Verify state thật | Sau apply **luôn** `kubectl get/describe` xác nhận đúng rồi mới chuyển câu |
| Namespace riêng | Set 1 lần đầu giờ: `kubectl config set-context --current --namespace=<ns-của-bạn>` |
| Tối thiểu 10đ nếu đúng | Cứ giải đúng, đừng bỏ câu |

**Mấu chốt:** YAML thuộc lòng + `kubectl explain` để tra field + imperative generator để khỏi gõ khung tay.

## ⚡ Imperative generator — VŨ KHÍ SỐ 1
Sinh YAML sẵn rồi sửa, thay vì gõ từ đầu:
```bash
# Pod
kubectl run web --image=nginx:1.27 --port=80 --dry-run=client -o yaml
# Deployment 3 replica
kubectl create deployment web --image=nginx:1.27 --replicas=3 --dry-run=client -o yaml
# Service (expose deployment)
kubectl expose deployment web --port=80 --target-port=80 --type=NodePort --dry-run=client -o yaml
# ConfigMap từ literal
kubectl create configmap app-cfg --from-literal=APP_ENV=prod --from-literal=LOG=info --dry-run=client -o yaml
# Thêm vào file rồi apply:
kubectl create deployment web --image=nginx --replicas=3 --dry-run=client -o yaml > d.yaml
kubectl apply -f d.yaml
```
> `kubectl explain pod.spec.containers` — tra field ngay trong terminal (không tốn điểm).

---

## 1. POD
```yaml
apiVersion: v1
kind: Pod
metadata:
  name: web
  labels:
    app: web
spec:
  containers:
    - name: nginx
      image: nginx:1.27
      ports:
        - containerPort: 80
```
Pod chạy lệnh (busybox):
```yaml
spec:
  containers:
    - name: busy
      image: busybox:1.36
      command: ["sh", "-c", "sleep 3600"]
```

## 2. DEPLOYMENT & replicas
```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: web
  labels:
    app: web
spec:
  replicas: 3
  selector:
    matchLabels:
      app: web        # PHẢI khớp template.labels bên dưới
  template:
    metadata:
      labels:
        app: web
    spec:
      containers:
        - name: web
          image: nginx:1.27
          ports:
            - containerPort: 80
```
Scale: `kubectl scale deploy/web --replicas=5`
Đổi image (rollout): `kubectl set image deploy/web web=nginx:1.28`

## 3. SERVICE
```yaml
apiVersion: v1
kind: Service
metadata:
  name: web
spec:
  type: ClusterIP        # hoặc NodePort / LoadBalancer
  selector:
    app: web             # tìm Pod qua label này
  ports:
    - port: 80           # cổng của Service
      targetPort: 80     # cổng trong Pod
      # nodePort: 30080  # CHỈ khi type: NodePort (30000-32767)
```
- **ClusterIP**: nội bộ cluster · **NodePort**: mở cổng trên node · **LoadBalancer**: LB cloud
- `kubectl expose deploy web --port=80 --target-port=80 --type=NodePort`

## 4. CONFIGMAP
```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: app-cfg
data:
  APP_ENV: "production"
  API_URL: "http://api:8080"
```
**Inject — toàn bộ key thành env** (envFrom):
```yaml
      envFrom:
        - configMapRef:
            name: app-cfg
```
**Inject — 1 key** (valueFrom):
```yaml
      env:
        - name: APP_ENV
          valueFrom:
            configMapKeyRef:
              name: app-cfg
              key: APP_ENV
```
**Mount thành file** (volume):
```yaml
      volumeMounts:
        - name: cfg
          mountPath: /etc/config
  volumes:
    - name: cfg
      configMap:
        name: app-cfg
```
> Secret tương tự: `secretKeyRef`, `secretRef`, `valueFrom`. Secret data phải base64.

## 5. LABELS & SELECTORS
```yaml
metadata:
  labels:
    app: web
    tier: frontend
```
```bash
kubectl label pod web tier=frontend            # thêm label
kubectl label pod web tier-                    # xoá label (dấu - cuối)
kubectl get pods -l app=web                    # lọc
kubectl get pods -l app=web,tier=frontend      # AND
kubectl get pods -l 'env in (dev,prod)'        # set-based
kubectl get pods --show-labels
```
> **Lỗi kinh điển:** `selector.matchLabels` (Deployment/Service) KHÔNG khớp `template.labels` → 0 Pod / Service không thấy Pod.

## 6. RESOURCES (requests / limits)
```yaml
      resources:
        requests:                 # tối thiểu được đảm bảo (scheduler dùng)
          cpu: "100m"             # 100m = 0.1 core
          memory: "128Mi"
        limits:                   # trần cứng
          cpu: "500m"
          memory: "256Mi"
```
- Vượt **memory** limit → container **OOMKilled** (kill + restart)
- Vượt **cpu** limit → bị **throttle** (không kill)
- `m` = milli-core · `Mi` = mebibyte, `Gi` = gibibyte

**Probes (hay đi kèm):**
```yaml
      readinessProbe:                 # sẵn sàng nhận traffic chưa? fail → gỡ khỏi Service
        httpGet: { path: /, port: 80 }
        initialDelaySeconds: 3
        periodSeconds: 5
      livenessProbe:                  # còn sống không? fail → restart
        httpGet: { path: /, port: 80 }
        periodSeconds: 10
```

## 🔍 kubectl verify (sau mỗi apply)
```bash
kubectl apply -f x.yaml
kubectl get pods,deploy,svc,cm -o wide
kubectl get pods --show-labels
kubectl describe pod <name>        # Events ở cuối — debug số 1
kubectl logs <pod>
kubectl exec <pod> -- env | grep APP_ENV     # check configmap đã inject
kubectl get deploy web -o yaml               # xem state thật
```

## ⚡ MẸO LÀM BÀI
- **Sinh khung bằng imperative** rồi sửa (Pod/Deployment/Service/ConfigMap) → tiết kiệm 60-80% thời gian gõ.
- **`--dry-run=server`** để validate trước khi apply thật → tránh sai >3 lần.
- **`kubectl explain <path>`** thay vì bấm Gợi ý (−25đ).
- Sau apply: `kubectl get` xác nhận đúng số replica / label / port rồi mới sang câu.
- Lỗi YAML hay gặp: **indent sai** (YAML 2 space, không tab), thiếu `-` ở list, `selector` không khớp `labels`, quên `targetPort`.
- **KHÔNG** Alt-Tab / mở DevTools / thoát full màn hình → khoá ngay.

## 🧪 TỰ LUYỆN trước giờ G
Có cụm minikube/kind sẵn? Gõ lại từng pattern, `kubectl apply --dry-run=server -f` để check.
Bấm giờ: ép mỗi câu < 90s (để dư buffer dưới mốc 120s).

---

# 📝 ĐỀ THỬ (20 câu) — tự làm rồi mới xem đáp án

> Đọc đề → che "Giải" → tự viết YAML / lệnh → bấm giờ < 120s → đối chiếu.

## NHÓM A — Pod

**Câu 1.** Tạo Pod `web`, image `nginx:1.27`, label `app=web`, mở port 80.
<details><summary>Giải</summary>

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: web
  labels: { app: web }
spec:
  containers:
    - name: nginx
      image: nginx:1.27
      ports:
        - containerPort: 80
```
Nhanh: `kubectl run web --image=nginx:1.27 --port=80 -l app=web`
</details>

**Câu 2.** Tạo Pod `busy` image `busybox:1.36` chạy `sleep 3600`.
<details><summary>Giải</summary>

```yaml
apiVersion: v1
kind: Pod
metadata: { name: busy }
spec:
  containers:
    - name: busy
      image: busybox:1.36
      command: ["sh", "-c", "sleep 3600"]
```
Nhanh: `kubectl run busy --image=busybox:1.36 --command -- sh -c "sleep 3600"`
</details>

**Câu 3.** Pod `app` image nginx, có env `APP_ENV=production`.
<details><summary>Giải</summary>

```yaml
apiVersion: v1
kind: Pod
metadata: { name: app }
spec:
  containers:
    - name: app
      image: nginx
      env:
        - name: APP_ENV
          value: "production"
```
</details>

## NHÓM B — Deployment & replicas

**Câu 4.** Deployment `api` 3 replica, image nginx:1.27, label `app=api`.
<details><summary>Giải</summary>

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: api
  labels: { app: api }
spec:
  replicas: 3
  selector:
    matchLabels: { app: api }
  template:
    metadata:
      labels: { app: api }
    spec:
      containers:
        - name: api
          image: nginx:1.27
```
Nhanh: `kubectl create deployment api --image=nginx:1.27 --replicas=3`
</details>

**Câu 5.** Scale deployment `api` lên 5 replica.
<details><summary>Giải</summary>

```bash
kubectl scale deployment/api --replicas=5
```
Hoặc sửa `spec.replicas: 5` rồi `kubectl apply`.
</details>

**Câu 6.** Deployment `web` 2 replica, container có requests cpu 100m/mem 128Mi, limits cpu 500m/mem 256Mi.
<details><summary>Giải</summary>

```yaml
apiVersion: apps/v1
kind: Deployment
metadata: { name: web, labels: { app: web } }
spec:
  replicas: 2
  selector: { matchLabels: { app: web } }
  template:
    metadata: { labels: { app: web } }
    spec:
      containers:
        - name: web
          image: nginx:1.27
          resources:
            requests: { cpu: "100m", memory: "128Mi" }
            limits:   { cpu: "500m", memory: "256Mi" }
```
</details>

## NHÓM C — Service

**Câu 7.** ClusterIP service `web` cho Pod `app=web`, Service port 80 → Pod port 8080.
<details><summary>Giải</summary>

```yaml
apiVersion: v1
kind: Service
metadata: { name: web }
spec:
  type: ClusterIP
  selector: { app: web }
  ports:
    - port: 80
      targetPort: 8080
```
</details>

**Câu 8.** NodePort service `web` cho `app=web`, port 80, nodePort 30080.
<details><summary>Giải</summary>

```yaml
apiVersion: v1
kind: Service
metadata: { name: web }
spec:
  type: NodePort
  selector: { app: web }
  ports:
    - port: 80
      targetPort: 80
      nodePort: 30080
```
Nhanh: `kubectl expose deploy web --port=80 --target-port=80 --type=NodePort` (rồi sửa nodePort nếu cần).
</details>

## NHÓM D — ConfigMap

**Câu 9.** ConfigMap `app-cfg` với `APP_ENV=prod`, `LOG_LEVEL=info`.
<details><summary>Giải</summary>

```yaml
apiVersion: v1
kind: ConfigMap
metadata: { name: app-cfg }
data:
  APP_ENV: "prod"
  LOG_LEVEL: "info"
```
Nhanh: `kubectl create configmap app-cfg --from-literal=APP_ENV=prod --from-literal=LOG_LEVEL=info`
</details>

**Câu 10.** Inject TOÀN BỘ `app-cfg` thành env trong Pod nginx.
<details><summary>Giải</summary>

```yaml
spec:
  containers:
    - name: app
      image: nginx
      envFrom:
        - configMapRef:
            name: app-cfg
```
</details>

**Câu 11.** Inject CHỈ key `APP_ENV` của `app-cfg` thành env `APP_ENV`.
<details><summary>Giải</summary>

```yaml
      env:
        - name: APP_ENV
          valueFrom:
            configMapKeyRef:
              name: app-cfg
              key: APP_ENV
```
</details>

**Câu 12.** Mount `app-cfg` thành file ở `/etc/config` trong Pod.
<details><summary>Giải</summary>

```yaml
spec:
  containers:
    - name: app
      image: nginx
      volumeMounts:
        - name: cfg
          mountPath: /etc/config
  volumes:
    - name: cfg
      configMap:
        name: app-cfg
```
</details>

## NHÓM E — Labels

**Câu 13.** Thêm label `tier=frontend` vào Pod `web` (imperative).
<details><summary>Giải</summary>

```bash
kubectl label pod web tier=frontend
```
Xoá: `kubectl label pod web tier-`
</details>

**Câu 14.** Liệt kê Pod có label `app=web` VÀ `tier=frontend`.
<details><summary>Giải</summary>

```bash
kubectl get pods -l app=web,tier=frontend
```
</details>

**Câu 15.** Deployment dưới đây 0 Pod chạy — vì sao? Sửa lại.
```yaml
spec:
  selector: { matchLabels: { app: web } }
  template:
    metadata: { labels: { app: api } }   # <-- lệch
```
<details><summary>Giải</summary>

`selector.matchLabels (app: web)` KHÔNG khớp `template.labels (app: api)`.
Sửa cho khớp:
```yaml
  template:
    metadata: { labels: { app: web } }
```
</details>

## NHÓM F — Resources & probes

**Câu 16.** Pod `web` nginx với requests cpu 250m/mem 64Mi, limits cpu 500m/mem 128Mi.
<details><summary>Giải</summary>

```yaml
spec:
  containers:
    - name: web
      image: nginx
      resources:
        requests: { cpu: "250m", memory: "64Mi" }
        limits:   { cpu: "500m", memory: "128Mi" }
```
</details>

**Câu 17.** Container vượt memory limit thì sao? Vượt cpu limit thì sao?
<details><summary>Giải</summary>

- Vượt **memory** limit → **OOMKilled** (bị giết + restart).
- Vượt **cpu** limit → bị **throttle** (chậm lại, không bị giết).
</details>

**Câu 18.** Deployment `web` 2 replica + readinessProbe HTTP GET `/` port 80, delay 3s.
<details><summary>Giải</summary>

```yaml
      containers:
        - name: web
          image: nginx:1.27
          ports: [{ containerPort: 80 }]
          readinessProbe:
            httpGet: { path: /, port: 80 }
            initialDelaySeconds: 3
            periodSeconds: 5
```
(đặt trong `template.spec.containers`)
</details>

## NHÓM G — Mixed

**Câu 19.** Expose deployment `web` thành NodePort port 80 bằng 1 lệnh.
<details><summary>Giải</summary>

```bash
kubectl expose deployment web --port=80 --target-port=80 --type=NodePort
```
</details>

**Câu 20.** Pod `multi` có 2 container (nginx + busybox) share 1 volume emptyDir tại `/data`.
<details><summary>Giải</summary>

```yaml
apiVersion: v1
kind: Pod
metadata: { name: multi }
spec:
  containers:
    - name: nginx
      image: nginx
      volumeMounts: [{ name: shared, mountPath: /data }]
    - name: busy
      image: busybox:1.36
      command: ["sh","-c","sleep 3600"]
      volumeMounts: [{ name: shared, mountPath: /data }]
  volumes:
    - name: shared
      emptyDir: {}
```
</details>

---

## ✅ Tự chấm
Làm 20 câu **< 30 phút** + dùng `kubectl explain`/Docs thay vì hint ⇒ sẵn sàng cho Test 2.
Câu nào ngắc ngứ → quay lại pattern tương ứng (mục 1-6) học lại + nhớ **imperative generator** để gõ nhanh.
