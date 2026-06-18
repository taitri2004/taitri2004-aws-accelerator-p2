# Chaos đơn giản: xoá 1 pod theo selector rồi quan sát Deployment tự tạo lại.
# Steady-state: số pod Ready quay về như cũ trong vài giây.
param(
    [string]$Namespace = "platform-app",
    [string]$Selector = "app=web"
)

Write-Host "== Trang thai truoc ==" -ForegroundColor Cyan
kubectl -n $Namespace get pods -l $Selector

$target = kubectl -n $Namespace get pods -l $Selector -o jsonpath='{.items[0].metadata.name}'
if (-not $target) { Write-Host "Khong tim thay pod khop selector '$Selector'." -ForegroundColor Yellow; exit 1 }

Write-Host "`n== Inject: xoa pod $target ==" -ForegroundColor Yellow
kubectl -n $Namespace delete pod $target

Write-Host "`n== Quan sat self-heal (10s) ==" -ForegroundColor Cyan
Start-Sleep -Seconds 10
kubectl -n $Namespace get pods -l $Selector

Write-Host "`nKy vong: pod moi da Running, tong so pod Ready khong doi." -ForegroundColor Green
