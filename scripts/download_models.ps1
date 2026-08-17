# H3 Studio 模型权重下载脚本(断点续传)
# 用法: powershell -ExecutionPolicy Bypass -File scripts\download_models.ps1 [-NoConfirm]
# 说明:
#   - NoobAI-XL / Krea-2 系列:从 hf-mirror.com 直接下载(中国大陆可达)
#   - MiniMax H3 权重:社区 pruned/nvfp4 转换版,请按 T8 节点仓库的安装说明获取
#     (官方原始权重: https://huggingface.co/MiniMaxAI/MiniMax-H3 )
#   - 重要: 各模型权重均有独立许可证与地区限制,使用前请阅读 NOTICE.md

param([switch]$NoConfirm)

$ErrorActionPreference = 'Continue'
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$repoRoot  = Split-Path -Parent $scriptDir
$models    = Join-Path $repoRoot 'models'

if (-not $NoConfirm) {
    Write-Host @"
=== 模型权重下载 ===
将下载约 30GB(不含 H3 主权重,它需按指引手动获取)。
各权重许可:
  - NoobAI-XL 1.0         CC-BY-NC-SA-4.0(非商用)
  - Krea-2-Turbo NVFP4    见 Comfy-Org/Krea-2 仓库声明
  - MiniMax H3            官方 Community License(排除美/欧/英/韩等地区)
详见 NOTICE.md。继续? [Y/N]
"@ -ForegroundColor Yellow
    $ans = Read-Host
    if ($ans -notin @('Y','y','yes','YES')) { Write-Host '已取消'; exit 0 }
}

# ---------- 下载清单: 目标目录 / 文件名 / 目标大小MB / URL ----------
$jobs = @(
    @{ dir='checkpoints';     name='NoobAI-XL-v1.0.safetensors';              size=6617; url='https://hf-mirror.com/Laxhar/noobai-XL-1.0/resolve/main/NoobAI-XL-v1.0.safetensors' },
    @{ dir='diffusion_models';name='krea2_turbo_nvfp4.safetensors';            size=7318; url='https://hf-mirror.com/Comfy-Org/Krea-2/resolve/main/diffusion_models/krea2_turbo_nvfp4.safetensors' },
    @{ dir='text_encoders';   name='qwen3vl_4b_fp8_scaled.safetensors';        size=5000; url='https://hf-mirror.com/Comfy-Org/Krea-2/resolve/main/text_encoders/qwen3vl_4b_fp8_scaled.safetensors' },
    @{ dir='vae';             name='qwen_image_vae.safetensors';               size=242;  url='https://hf-mirror.com/Comfy-Org/Krea-2/resolve/main/vae/qwen_image_vae.safetensors' },
    @{ dir='loras';           name='krea2_style_reference.safetensors';        size=436;  url='https://hf-mirror.com/Comfy-Org/Krea-2/resolve/main/loras/krea2_style_reference.safetensors' }
)

# ---------- MiniMax H3 权重清单(需手动获取,文件名必须一致) ----------
$h3Files = @(
    @{ dir='diffusion_models'; name='minimax_h3_fl2va_pruned_int8_convrot.safetensors'; size=19999 },
    @{ dir='diffusion_models'; name='minimax_h3_ref2va_pruned_int8_convrot.safetensors'; size=19999 },
    @{ dir='text_encoders';    name='qwen3vl_32b_minimax_h3_nvfp4_awq.safetensors';       size=14960 },
    @{ dir='vae';              name='minimax_h3_video_vae_fp16.safetensors';              size=4967 },
    @{ dir='vae';              name='minimax_h3_audio_vae_fp32.safetensors';              size=577 }
)

# ---------- 执行下载 ----------
foreach ($j in $jobs) {
    $dir = Join-Path $models $j.dir
    New-Item -ItemType Directory -Force -Path $dir | Out-Null
    $out = Join-Path $dir $j.name
    if (Test-Path $out) {
        $cur = [math]::Round((Get-Item $out).Length / 1MB)
        if ($cur -ge $j.size - 5) { Write-Host "[SKIP] $($j.name) 已存在($cur MB)" -ForegroundColor DarkGray; continue }
        Write-Host "[RESUME] $($j.name) 续传中(现有 $cur / $($j.size) MB)..."
    } else {
        Write-Host "[GET] $($j.name) ($($j.size) MB)..."
    }
    curl.exe -L -C - --fail --retry 8 --retry-delay 5 -o $out $j.url
    $now = [math]::Round((Get-Item $out -ErrorAction SilentlyContinue).Length / 1MB)
    if ($now -ge $j.size - 5) { Write-Host "    OK ($now MB)" -ForegroundColor Green }
    else { Write-Host "    [WARN] 大小异常($now MB),可能未完成或源文件有变" -ForegroundColor Red }
}

# ---------- H3 权重检查 ----------
Write-Host ''
Write-Host '=== MiniMax H3 权重检查 ===' -ForegroundColor Cyan
$missing = 0
foreach ($f in $h3Files) {
    $p = Join-Path $models (Join-Path $f.dir $f.name)
    if (Test-Path $p) { Write-Host "  [OK] $($f.name)" -ForegroundColor Green }
    else { Write-Host "  [MISS] $($f.name)(需 $($f.size) MB)" -ForegroundColor Red; $missing++ }
}
if ($missing) {
    Write-Host @"

H3 主权重缺失($missing 个)。获取方式:
  1. 官方原始权重:  https://huggingface.co/MiniMaxAI/MiniMax-H3
     (注意 Community License 地区限制,见 NOTICE.md)
  2. 本面板使用社区 pruned int8 / nvfp4 转换版(8GB 显存必需),
     请参考 T8 节点仓库 comfyui-minimax-h3-audio-T8 的安装说明,
     将文件放入 models\ 对应子目录并保持文件名一致。
"@ -ForegroundColor Yellow
} else {
    Write-Host 'H3 权重齐全。' -ForegroundColor Green
}

Write-Host ''
Write-Host '=== 完成 ==='
Write-Host '下一步: scripts\launcher.ps1 启动(首次启动会加载模型,请耐心等待)' -ForegroundColor Yellow
