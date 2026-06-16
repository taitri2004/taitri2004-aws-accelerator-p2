# Kiểm chứng 3 role bằng impersonation. Chạy sau khi apply rbac/.
# Kỳ vọng in ra đúng yes/no cho từng ô của ma trận quyền.

$ns = "w10-demo"
$viewer    = "system:serviceaccount:$ns`:viewer"
$developer = "system:serviceaccount:$ns`:developer"
$sre       = "system:serviceaccount:$ns`:sre"

function Check($who, $verb, $resource, $expect) {
    # Retry vài lần: trên cluster nhỏ/đang tải, call đầu có thể timeout -> rỗng.
    $ans = ""
    for ($try = 0; $try -lt 3 -and [string]::IsNullOrWhiteSpace($ans); $try++) {
        if ($try -gt 0) { Start-Sleep -Milliseconds 500 }
        $ans = (kubectl auth can-i $verb $resource --as=$who -n $ns 2>$null | Select-Object -First 1)
    }
    $mark = if ($ans -eq $expect) { "OK " } else { "XX " }
    "{0} {1,-9} {2,-22} as {3,-12} -> {4} (expect {5})" -f $mark, $verb, $resource, $who.Split(':')[-1], $ans, $expect
}

Write-Host "=== viewer: chi doc ===" -ForegroundColor Cyan
Check $viewer    "list"   "pods"            "yes"
Check $viewer    "get"    "deployments.apps" "yes"
Check $viewer    "create" "deployments.apps" "no"
Check $viewer    "get"    "secrets"          "no"

Write-Host "=== developer: quan workload, khong so RBAC/namespace ===" -ForegroundColor Cyan
Check $developer "create" "deployments.apps"            "yes"
Check $developer "delete" "pods"                        "yes"
Check $developer "get"    "secrets"                     "yes"
Check $developer "create" "namespaces"                  "no"
Check $developer "create" "rolebindings.rbac.authorization.k8s.io" "no"

Write-Host "=== sre: cross-namespace + Gatekeeper, KHONG ghi RBAC ===" -ForegroundColor Cyan
Check $sre       "list"   "nodes"                       "yes"
Check $sre       "delete" "pods"                        "yes"
Check $sre       "create" "k8srequiredlabels.constraints.gatekeeper.sh" "yes"
Check $sre       "create" "resourcequotas"              "yes"
Check $sre       "create" "clusterrolebindings.rbac.authorization.k8s.io" "no"

Write-Host "`nLiet ke toan bo quyen cua developer:" -ForegroundColor Cyan
kubectl auth can-i --list --as=$developer -n $ns
