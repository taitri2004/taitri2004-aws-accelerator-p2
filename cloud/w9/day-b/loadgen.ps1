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
