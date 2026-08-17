# H3 Studio Installer - 一键搭建 ComfyUI + H3 Studio 环境(Windows)
# 用法: powershell -ExecutionPolicy Bypass -File scripts\install.ps1
# 功能: 1) 获取 ComfyUI 源码  2) 创建 venv + torch(cu130)  3) 安装 3 个自定义节点  4) 生成 extra_model_paths.yaml
# 注意: 模型权重不在此脚本下载,请另行运行 scripts\download_models.ps1(见 NOTICE.md 许可说明)

$ErrorActionPreference = 'Stop'
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$repoRoot  = Split-Path -Parent $scriptDir
$comfyDir  = Join-Path $repoRoot 'ComfyUI'
$srcDir    = Join-Path $comfyDir 'ComfyUI-master'
$venvPy    = Join-Path $comfyDir 'venv\Scripts\python.exe'

Write-Host '=== H3 Studio Installer ===' -ForegroundColor Cyan
Write-Host "仓库根: $repoRoot"

# ---------- 1. ComfyUI 源码 ----------
if (Test-Path (Join-Path $srcDir 'main.py')) {
    Write-Host '[1/5] ComfyUI 源码已存在,跳过' -ForegroundColor Green
} else {
    Write-Host '[1/5] 获取 ComfyUI 源码...' -ForegroundColor Yellow
    New-Item -ItemType Directory -Force -Path $comfyDir | Out-Null
    git clone --depth 1 https://github.com/comfyanonymous/ComfyUI.git $srcDir 2>$null
    if (-not (Test-Path (Join-Path $srcDir 'main.py'))) {
        Write-Host @"

[ERROR] git clone 失败(GitHub 主域可能无法访问)。
备选方案(任选其一):
  1. 使用镜像:  git clone --depth 1 https://gitclone.com/github.com/comfyanonymous/ComfyUI.git $srcDir
  2. 手动下载:  浏览器打开 https://codeload.github.com/comfyanonymous/ComfyUI/zip/refs/heads/master
                 解压 zip 到 $srcDir(保持目录名 ComfyUI-master)
完成后重新运行本脚本。
"@ -ForegroundColor Red
        Read-Host 'Press Enter to exit'; exit 1
    }
    Write-Host '    完成' -ForegroundColor Green
}

# ---------- 2. venv ----------
$needVenv = -not (Test-Path $venvPy)
if (-not $needVenv) {
    Write-Host '[2/5] venv 已存在,跳过' -ForegroundColor Green
} else {
    Write-Host '[2/5] 创建虚拟环境...' -ForegroundColor Yellow
    $haveUv = Get-Command uv -ErrorAction SilentlyContinue
    if ($haveUv) {
        Push-Location $comfyDir
        uv venv venv --python 3.12 2>$null
        Pop-Location
    } else {
        python -m venv (Join-Path $comfyDir 'venv') 2>$null
    }
    if (-not (Test-Path $venvPy)) {
        Write-Host '[ERROR] venv 创建失败,请确认已安装 Python 3.10+ 或 uv' -ForegroundColor Red
        Read-Host 'Press Enter to exit'; exit 1
    }
    Write-Host '    完成' -ForegroundColor Green
}

# ---------- 3. torch + ComfyUI 依赖 ----------
Write-Host '[3/5] 安装 torch 2.9.x + cu130 与依赖(约 3-4GB,耗时较长)...' -ForegroundColor Yellow
# 阿里云 pytorch-wheels 镜像(cu130),需用 --find-links 而非 --index-url
& $venvPy -m pip install --upgrade pip --quiet 2>$null
& $venvPy -m pip install --find-links https://mirrors.aliyun.com/pytorch-wheels/cu130/ torch torchvision torchaudio --quiet 2>$null
if ($LASTEXITCODE -ne 0) {
    Write-Host '[WARN] 阿里云镜像安装失败,尝试官方源(可能较慢)...' -ForegroundColor Yellow
    & $venvPy -m pip install torch torchvision torchaudio --quiet 2>$null
}
& $venvPy -m pip install -r (Join-Path $srcDir 'requirements.txt') --quiet 2>$null
Write-Host '    完成' -ForegroundColor Green

# ---------- 4. 自定义节点 ----------
$cnDir = Join-Path $srcDir 'custom_nodes'
New-Item -ItemType Directory -Force -Path $cnDir | Out-Null
$nodes = @(
    @{ name = 'ComfyUI-VideoHelperSuite'; zip = 'https://codeload.github.com/Kosinkadink/ComfyUI-VideoHelperSuite/zip/refs/heads/main' },
    @{ name = 'ComfyUI-KJNodes';          zip = 'https://codeload.github.com/kijai/ComfyUI-KJNodes/zip/refs/heads/main' },
    @{ name = 'comfyui-minimax-h3-audio-T8'; zip = 'https://codeload.github.com/T8mars/comfyui-minimax-h3-audio-T8/zip/refs/heads/main' }
)
# 注意:T8 节点仓库名以 kijai 为例,请以该节点作者仓库实际地址为准;若 404 请手动下载解压到 custom_nodes
foreach ($nd in $nodes) {
    $target = Join-Path $cnDir $nd.name
    if (Test-Path $target) { Write-Host "    [SKIP] $($nd.name) 已存在" -ForegroundColor DarkGray; continue }
    Write-Host "    下载节点: $($nd.name) ..." -ForegroundColor Yellow
    $zip = Join-Path $env:TEMP ($nd.name + '.zip')
    curl.exe -L -s --retry 3 -o $zip $nd.zip
    if (Test-Path $zip) {
        $tmp = Join-Path $env:TEMP ($nd.name + '_x')
        Remove-Item $tmp -Recurse -Force -ErrorAction SilentlyContinue
        Expand-Archive -Path $zip -DestinationPath $tmp -Force
        $inner = Get-ChildItem $tmp -Directory | Select-Object -First 1
        if ($inner) { Move-Item $inner.FullName $target -Force }
        Remove-Item $tmp -Recurse -Force -ErrorAction SilentlyContinue
        Remove-Item $zip -Force -ErrorAction SilentlyContinue
    }
    if (-not (Test-Path $target)) { Write-Host "    [WARN] $($nd.name) 下载失败,请手动安装到 $cnDir" -ForegroundColor Red }
}
# h3-studio-web:从本仓库复制
Copy-Item (Join-Path $repoRoot 'custom_nodes\h3-studio-web') $cnDir -Recurse -Force
Write-Host '    完成' -ForegroundColor Green

# ---------- 5. extra_model_paths.yaml ----------
$yaml = Join-Path $srcDir 'extra_model_paths.yaml'
if (-not (Test-Path $yaml)) {
    @"
# H3 Studio 模型目录映射(权重由 download_models.ps1 放入)
h3_studio:
    checkpoints: $repoRoot\models\checkpoints
    diffusion_models: $repoRoot\models\diffusion_models
    text_encoders: $repoRoot\models\text_encoders
    vae: $repoRoot\models\vae
    loras: $repoRoot\models\loras
"@ | Set-Content -Path $yaml -Encoding UTF8
    Write-Host '[5/5] 已生成 extra_model_paths.yaml' -ForegroundColor Green
} else {
    Write-Host '[5/5] extra_model_paths.yaml 已存在(如需更新请手动编辑)' -ForegroundColor DarkGray
}

Write-Host ''
Write-Host '=== 安装完成 ===' -ForegroundColor Cyan
Write-Host "下一步: 运行 scripts\download_models.ps1 下载模型权重,然后 scripts\launcher.ps1 启动。" -ForegroundColor Yellow
