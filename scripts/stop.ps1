# H3 Studio Stop - 停止 ComfyUI(端口持有者 + 全部 main.py 进程双保险)
# 用法: powershell -ExecutionPolicy Bypass -File scripts\stop.ps1

Write-Host 'Stopping ComfyUI ...'

# 1. 结束占用 8188 端口的进程
$conn = Get-NetTCPConnection -LocalPort 8188 -State Listen -ErrorAction SilentlyContinue
if ($conn) {
    foreach ($c in $conn) {
        Write-Host "Stopped port owner PID $($c.OwningProcess)"
        Stop-Process -Id $c.OwningProcess -Force -ErrorAction SilentlyContinue
    }
    Start-Sleep -Seconds 2
} else {
    Write-Host 'No process listening on port 8188.'
}

# 2. 清理残余 main.py 进程(uv 重定向器/解释器双进程场景)
$procs = Get-CimInstance Win32_Process -Filter "Name='python.exe'" -ErrorAction SilentlyContinue |
    Where-Object { $_.CommandLine -like '*main.py*' }
foreach ($pr in $procs) {
    Write-Host "Stopped PID $($pr.ProcessId)"
    Stop-Process -Id $pr.ProcessId -Force -ErrorAction SilentlyContinue
}

Start-Sleep -Seconds 2
$still = Get-NetTCPConnection -LocalPort 8188 -State Listen -ErrorAction SilentlyContinue
if ($still) { Write-Host '[WARN] Port 8188 still occupied' -ForegroundColor Red }
else { Write-Host 'Done. ComfyUI stopped.' -ForegroundColor Green }
