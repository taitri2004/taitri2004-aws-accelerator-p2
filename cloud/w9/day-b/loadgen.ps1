# Load generator cho demo burn rate.
# Bắn request liên tục vào podinfo, một tỉ lệ trả 500 (qua endpoint /status/500)
# để đẩy error ratio vượt ngưỡng burn rate => alert fire.
#
# Yêu cầu: đã port-forward podinfo trước:
#   kubectl -n demo port-forward svc/podinfo 9898:9898
#
# Cách dùng:
#   .\loadgen.ps1                 # mặc định 50% lỗi trong 300s
#   .\loadgen.ps1 -ErrorRate 0.8 -DurationSec 600

param(
  [double]$ErrorRate = 0.5,
  [int]$DurationSec = 300,
  [string]$BaseUrl = "http://localhost:9898"
)

$deadline = (Get-Date).AddSeconds($DurationSec)
$ok = 0; $err = 0
Write-Host "Generating load: error rate $ErrorRate for ${DurationSec}s -> $BaseUrl"
while ((Get-Date) -lt $deadline) {
  if ((Get-Random -Minimum 0.0 -Maximum 1.0) -lt $ErrorRate) {
    curl.exe -s -o NUL "$BaseUrl/status/500"; $err++
  } else {
    curl.exe -s -o NUL "$BaseUrl/"; $ok++
  }
  if ((($ok + $err) % 50) -eq 0) { Write-Host "ok=$ok err=$err" }
}
Write-Host "Done. ok=$ok err=$err total=$($ok + $err)"
