# H3 Studio · MiniMax H3 本地出片工作台

**[中文](README.md) | [English](README.en.md)**

> 在 **8GB 显存** 的消费级显卡上跑通 MiniMax H3(33B 全模态音视频扩散模型),并提供统一的中文 Web 工作台:H3 视频四模式 + 多镜头 + 提示词优化 + 专职图像模型(NoobAI-XL / Krea-2-Turbo)文生图/图生图,全部带本机实测基准数据。

![modes](https://img.shields.io/badge/modes-8-green) ![vram](https://img.shields.io/badge/VRAM-8GB%20OK-blue) ![comfyui](https://img.shields.io/badge/ComfyUI-0.33-orange)

---

## ✨ 功能

| 模式 | 说明 |
|---|---|
| 📝 T2VA | 文生视频(带原生同步音频) |
| 🖼️ I2VA | 首帧图生视频,自动匹配画布比例 |
| 🔄 FL2VA | 首尾帧视频 |
| 🧩 Ref2VA | 多参考(≤9 图 + ≤3 视频 + ≤3 音频)换人/换装/改风格 |
| 🎬 MULTI | 多镜头短片:分镜 → 逐镜生成(自动首帧衔接)→ 一键 ffmpeg 拼接(硬切/叠化) |
| ✨ PROMPT | 大白话 → H3 最佳实践提示词(本地规则引擎,零依赖) |
| 🖼️ T2I / 🎨 I2I | 专职图像模型:NoobAI-XL(SDXL)、Krea-2-Turbo(NVFP4)与 **Qwen-Image-Edit 2511(GGUF)**,含负面提示词/denoise/加速 LoRA;**重绘模式(涂抹蒙版)** |
| ⚙️ SETTINGS | 设置页:每模式多版本提示词预设库、默认参数、模型状态检查、历史/预设导出导入 |

**特色**
- 生成历史(视频/图片可分开筛选,localStorage 持久化)
- 基准数据内嵌(视频 14 轮 + 图片 10 轮,按模式自动切换展示)
- 推荐参数一键应用(基于本机实测)
- 纯本地运行,无任何云端调用

---

## 🖥️ 硬件要求

**实测平台**:RTX 5060 **8GB** · i5-14600KF · 32GB RAM · Windows 11 · ComfyUI 0.33.0 · torch 2.9.1+cu130

| 配置 | 效果 |
|---|---|
| 8GB 显存(实测基线) | 视频 864×480 全模式可用,5秒·8步 ≈ 188 秒/条;生图 14-38 秒/张 |
| 12GB+ 显存 | 可尝试更大画布与更长时长 |
| 32GB RAM(推荐) | 模型换载需要系统内存 |

---

## 🚀 快速开始

```powershell
# 1. 搭建环境(获取 ComfyUI 源码 + venv + torch cu130 + 自定义节点)
powershell -ExecutionPolicy Bypass -File scripts\install.ps1

# 2. 下载模型权重(NoobAI/Krea 自动下载;H3 主权重按脚本指引获取)
powershell -ExecutionPolicy Bypass -File scripts\download_models.ps1

# 3. 启动并打开面板
powershell -ExecutionPolicy Bypass -File scripts\launcher.ps1
# 浏览器访问 http://127.0.0.1:8188/h3-studio
```

### 模型清单(放入 `models/` 对应子目录,文件名必须一致)

| 文件 | 大小 | 用途 | 许可 |
|---|---|---|---|
| `minimax_h3_fl2va_pruned_int8_convrot.safetensors` | 20.0GB | H3 文生/首尾帧视频 | H3 Community License |
| `minimax_h3_ref2va_pruned_int8_convrot.safetensors` | 20.0GB | H3 多参考/生图通道 | H3 Community License |
| `qwen3vl_32b_minimax_h3_nvfp4_awq.safetensors` | 15.0GB | H3 文本编码器 | H3 Community License |
| `minimax_h3_video_vae_fp16.safetensors` | 5.0GB | 视频 VAE | H3 Community License |
| `minimax_h3_audio_vae_fp32.safetensors` | 0.6GB | 音频 VAE | H3 Community License |
| `NoobAI-XL-v1.0.safetensors` | 6.6GB | 文生图/图生图(SDXL) | CC-BY-NC-SA-4.0 |
| `krea2_turbo_nvfp4.safetensors` | 7.3GB | Krea-2 生图 UNet | 见 Comfy-Org/Krea-2 |
| `qwen3vl_4b_fp8_scaled.safetensors` | 5.0GB | Krea-2 文本编码器 | 见 Comfy-Org/Krea-2 |
| `qwen_image_vae.safetensors` | 0.2GB | Krea-2 VAE | 见 Comfy-Org/Krea-2 |
| `krea2_style_reference.safetensors` | 0.4GB | Krea 风格参考 LoRA | 见 Comfy-Org/Krea-2 |
| `qwen-image-edit-2511-Q4_K_M.gguf` | 12.3GB | Qwen 图生图编辑 UNET(GGUF Q4) | Qwen 社区 GGUF 转换 |
| `qwen_2.5_vl_7b_fp8_scaled.safetensors` | 8.7GB | Qwen 文本编码器 | Comfy-Org / Qwen |
| `Qwen-Image-Lightning-8steps-V1.1-bf16.safetensors` | 0.8GB | Qwen 8 步加速 LoRA | Qwen-Image-Lightning |
| `Qwen-Image-InstantX-ControlNet-Inpainting.safetensors` | 4.0GB | Qwen 重绘蒙版 ControlNet | Comfy-Org/Qwen-Image-InstantX-ControlNets |

> ⚠️ **权重不随本仓库分发**,请通过 `download_models.ps1` 或原仓库获取。各权重许可与地区限制详见 [NOTICE.md](NOTICE.md)。

---

## 📊 实测基准(本仓库最有价值的部分)

### 视频(H3,864×480,RTX 5060 8GB)

| 模式 | 5秒·8步 | 10秒·8步 | 15秒·8步 | 15秒·20步 |
|---|---|---|---|---|
| T2VA | **188 秒** | 543 秒 | 898 秒 | 2043 秒(≈34 分钟) |
| I2VA | 188 秒 | 468 秒 | 985 秒 | — |
| FL2VA | 200 秒 | 513 秒 | 1078 秒(≈18 分钟) | — |
| Ref2VA | 188 秒 | 468 秒 | 985 秒 | — |

> 表中耗时单位均为**秒**。VRAM 峰值 7.0-7.7GB · GPU 均载 86-97% · 温度 66-70℃ · 20 步音频底噪 -17dB(8 步 -51dB)

### 图片(NoobAI / Krea,1024²)

| 模型 | 参数 | 耗时 | VRAM 峰值 |
|---|---|---|---|
| NoobAI-XL | 20步·cfg5 | 14-18 秒 | 7.2GB |
| NoobAI-XL | 图生图 dn0.75 | 10 秒 | 6.9GB |
| Krea-2-Turbo | 4步·cfg1 | 16 秒 | 7.5GB |
| Krea-2-Turbo | 8步·cfg1 | 26 秒 | 7.4GB |
| Qwen-Edit 2511 | 8步·cfg1(Lightning 加速) | 80-95 秒 | 7.4GB |
| Qwen-Edit 2511 | 20步·cfg4(标准) | 260 秒 | 7.4GB |

完整数据:`benchmark/`(results.json + 逐秒遥测 CSV + 复现脚本)

---

## 🧭 目录结构

```
h3-studio/
├─ custom_nodes/h3-studio-web/    # Web 面板本体(ComfyUI 自定义节点,路由 /h3-studio)
├─ workflows/                     # 现成 ComfyUI API 工作流 JSON
├─ benchmark/                     # 基准:视频 14 轮 / H3 生图 9 轮 / 图片 10 轮
│  ├─ bench_driver.py             #   视频基准(4 模式 × 时长 × 步数 + 遥测)
│  ├─ still/still_bench.py        #   H3 生图基准
│  ├─ img/img_bench.py            #   NoobAI/Krea 图片基准
│  └─ img/mode_switch_test.js     #   面板 UI 回归测试(桩 DOM,无需 ComfyUI)
├─ scripts/
│  ├─ install.ps1                 # 环境搭建
│  ├─ download_models.ps1         # 权重下载
│  ├─ launcher.ps1 / stop.ps1     # 启停
└─ docs/
   ├─ h3-prompt-library.md        # H3 提示词库(最佳实践模板)
   ├─ vram-tuning.md              # 8GB 显存调优实战(踩坑记录)
   └─ image-model-research.md     # 8GB 显存生图模型选型调研
```

---

## 🔧 依赖

- [ComfyUI](https://github.com/comfyanonymous/ComfyUI) ≥ 0.33(GPL-3.0)
- [comfyui-minimax-h3-audio-T8](https://github.com/T8mars/comfyui-minimax-h3-audio-T8)(H3 节点)
- [ComfyUI-VideoHelperSuite](https://github.com/Kosinkadink/ComfyUI-VideoHelperSuite)(视频输出)
- [ComfyUI-KJNodes](https://github.com/kijai/ComfyUI-KJNodes)
- Python 3.10+ · torch ≥2.9(cu130) · ffmpeg

---

## 📄 许可

- **本仓库代码**:GPL-3.0(与 ComfyUI 保持一致),见 [LICENSE](LICENSE)
- **模型权重**:各自独立许可,见 [NOTICE.md](NOTICE.md)——MiniMax H3 官方 Community License **排除美国/欧盟/英国/韩国等地区**;NoobAI-XL 为 CC-BY-NC-SA-4.0 非商用许可。使用前请务必确认你所在地区与用途合规。

---

## ⚠️ 免责声明

本仓库是**开源工具**,仅提供本地生成能力,不附带任何内容审核、过滤或拦截功能。**使用本项目生成的内容(包括但不限于图像、视频、音频与文字)完全由使用者本人负责**:

- 使用者须自行确认生成内容符合所在地法律法规、模型权重许可(见 NOTICE.md)以及相关平台的服务条款;
- 本项目可能生成不准确、不当或具有误导性的内容;请勿将其用于违法、侵权、欺诈、仇恨言论或任何可能伤害他人的场景;
- 作者与贡献者不对因使用、修改、分发本项目而产生的任何直接或间接损失、法律后果或第三方主张承担责任;
- 本声明不构成法律意见。

通过安装或使用本项目,即视为已阅读并同意上述条款。

---

## 🙏 致谢

- MiniMax 团队与 H3 开源社区
- [T8mars](https://github.com/T8mars) 与 ComfyUI 生态的节点作者们
- 所有致力于低显存本地 AI 部署与优化的开源作者

---

## Disclaimer (English)

This repository is an open-source **tool** that provides local generation capabilities only and includes **no content moderation, filtering, or blocking**. You are **solely responsible** for the content you generate with it, including but not limited to images, videos, audio, and text:

- Ensure your usage complies with your local laws, the model weight licenses (see [NOTICE.md](NOTICE.md)), and applicable platform terms of service;
- Generated content may be inaccurate, inappropriate, or misleading; do not use it for illegal, infringing, fraudulent, hateful, or harmful purposes;
- The authors and contributors are not liable for any direct or indirect damages, legal consequences, or third-party claims arising from the use, modification, or distribution of this project;
- This statement is not legal advice.

By installing or using this project, you acknowledge that you have read and agree to these terms.

---

*English summary: A local video/image generation workbench for MiniMax H3 (33B audio-video diffusion) that runs on 8GB VRAM consumer GPUs, with a Chinese web UI, multi-shot editing, prompt optimizer, and dedicated image backends (NoobAI-XL / Krea-2-Turbo). Includes reproducible benchmark scripts and telemetry data. Models are NOT included due to their own licenses (see NOTICE.md).*
