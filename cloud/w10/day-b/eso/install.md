# Cài External Secrets Operator + demo rotation

## Cài ESO

```powershell
helm repo add external-secrets https://charts.external-secrets.io; helm repo update
helm install external-secrets external-secrets/external-secrets `
  -n external-secrets --create-namespace --set installCRDs=true
kubectl -n external-secrets rollout status deploy/external-secrets
```

## Đường A — Local/offline (provider fake, không cần AWS)

```powershell
kubectl apply -f cloud/w10/day-b/eso/00-namespace.yaml
kubectl apply -f cloud/w10/day-b/eso/secretstore-fake.yaml
kubectl apply -f cloud/w10/day-b/eso/externalsecret-fake.yaml
kubectl apply -f cloud/w10/day-b/eso/consumer-deployment.yaml

# Secret K8s do ESO sinh ra
kubectl -n w10-secrets get secret app-secret -o jsonpath='{.data.db-password}' | %{ [Text.Encoding]::UTF8.GetString([Convert]::FromBase64String($_)) }
```

Quan sát rotation no-restart:

```powershell
# Terminal phụ: theo dõi consumer in giá trị mỗi 5s
kubectl -n w10-secrets logs -f deploy/secret-consumer

# Rotate: đổi value v1 -> v2 trong secretstore-fake.yaml rồi apply lại
#   (value: v2-rotated, version: v2)
kubectl apply -f cloud/w10/day-b/eso/secretstore-fake.yaml
```

Trong < 60s log consumer đổi sang `v2-rotated` mà pod KHÔNG restart
(`RESTARTS` giữ nguyên `kubectl -n w10-secrets get pods`).

## Đường B — AWS Secrets Manager thật (trên EKS, IRSA)

```powershell
# Tạo secret trên AWS
aws secretsmanager create-secret --name prod/app `
  --secret-string '{"db_password":"v1-from-aws"}' --region ap-southeast-1

# Điền <ACCOUNT_ID> vào 00-namespace.yaml (annotation IRSA), rồi:
kubectl apply -f cloud/w10/day-b/eso/00-namespace.yaml
kubectl apply -f cloud/w10/day-b/eso/secretstore-aws.yaml
kubectl apply -f cloud/w10/day-b/eso/externalsecret-aws.yaml
kubectl apply -f cloud/w10/day-b/eso/consumer-deployment.yaml

# Rotate ở AWS -> ESO sync trong refreshInterval
aws secretsmanager put-secret-value --secret-id prod/app `
  --secret-string '{"db_password":"v2-from-aws"}' --region ap-southeast-1
```

> Lưu ý chỉ apply MỘT ExternalSecret (fake HOẶC aws) vì cùng target `app-secret`.
