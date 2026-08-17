# H3 Studio Launcher - 启动 ComfyUI 并打开 H3 Studio 面板
# 用法: powershell -ExecutionPolicy Bypass -File scripts\launcher.ps1
# 依赖 scripts\install.ps1 已完成(仓库根/ComfyUI 布局)

$ErrorActionPreference = 'Continue'

# 路径全部基于脚本位置推导(仓库根 = scripts 的上一级)
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$repoRoot  = Split-Path -Parent $scriptDir
$comfyRoot = Join-Path $repoRoot 'ComfyUI\ComfyUI-master'
$py        = Join-Path $repoRoot 'ComfyUI\venv\Scripts\python.exe'
$log       = Join-Path $repoRoot 'comfyui.log'
$port      = 8188
$url       = "http://127.0.0.1:$port/h3-studio"
$stats     = "http://127.0.0.1:$port/system_stats"

Write-Host '=== H3 Studio Launcher ===' -ForegroundColor Cyan

function Test-ComfyUI {
    try {
        # 兼容 Windows PowerShell 5.1:-SkipHttpErrorCheck 仅 PS7+,不能使用
        $r = Invoke-WebRequest -Uri $stats -UseBasicParsing -TimeoutSec 3
        return ($r.StatusCode -eq 200 -and $r.Content -match '"devices"')
    } catch { return $false }
}

# 0. sanity checks
if (-not (Test-Path $py)) {
    Write-Host "[ERROR] Python env not found: $py" -ForegroundColor Red
    Write-Host "        请先运行 scripts\install.ps1 完成环境搭建" -ForegroundColor Yellow
    Read-Host 'Press Enter to exit'; exit 1
}
if (-not (Test-Path (Join-Path $comfyRoot 'main.py'))) {
    Write-Host "[ERROR] ComfyUI not found: $comfyRoot" -ForegroundColor Red
    Write-Host "        请先运行 scripts\install.ps1 完成环境搭建" -ForegroundColor Yellow
    Read-Host 'Press Enter to exit'; exit 1
}

# 1. is ComfyUI already up?
if (Test-ComfyUI) {
    Write-Host '[1/3] ComfyUI already running - skipping start' -ForegroundColor Green
} else {
    Write-Host '[1/3] Starting ComfyUI (first start takes ~30-60s)...' -ForegroundColor Yellow
    $args = @('main.py',
        '--windows-standalone-build','--enable-dynamic-vram','--fast-disk',
        '--cache-none','--reserve-vram','1.0','--disable-pinned-memory',
        '--port',"$port",'--disable-auto-launch')
    $p = Start-Process -FilePath $py -ArgumentList $args -WorkingDirectory $comfyRoot `
        -RedirectStandardOutput $log -RedirectStandardError "$log.err" -WindowStyle Hidden -PassThru

    $ok = $false
    # NOTE: uv 管理的 venv 使用重定向器 python.exe,可能先于真实解释器退出,
    # 因此不能用 $p.HasExited 判断失败,以端口就绪为准。
    for ($i = 0; $i -lt 90; $i++) {
        Start-Sleep -Seconds 3
        if (Test-ComfyUI) { $ok = $true; break }
    }
    if (-not $ok) {
        Write-Host '[ERROR] ComfyUI failed to start. See logs:' -ForegroundColor Red
        Write-Host "        $log / $log.err" -ForegroundColor Red
        Read-Host 'Press Enter to exit'; exit 1
    }
    Write-Host '[2/3] ComfyUI ready' -ForegroundColor Green
}

# 2. verify the H3 Studio route
try {
    $r = Invoke-WebRequest -Uri $url -UseBasicParsing -TimeoutSec 5
    Write-Host "[3/3] H3 Studio page ready (HTTP $($r.StatusCode))" -ForegroundColor Green
} catch {
    Write-Host '[3/3] Page route not ready yet - refresh browser if blank' -ForegroundColor Yellow
}

# 3. open the browser
Start-Process $url
Write-Host ''
Write-Host "Browser opened: $url" -ForegroundColor Cyan
Write-Host 'Note: closing this window does NOT stop ComfyUI.' -ForegroundColor DarkGray
Write-Host '      To stop it, run scripts\stop.ps1' -ForegroundColor DarkGray
