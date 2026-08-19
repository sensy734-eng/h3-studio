# H3 Studio · Local Generation Workbench for MiniMax H3

**[English](README.en.md) | [中文](README.md)**

> Run MiniMax H3 (33B multimodal audio-video diffusion) on an **8GB VRAM** consumer GPU, with a unified Chinese-first web workbench: four H3 video modes + multi-shot editing + prompt optimizer + dedicated image backends (NoobAI-XL / Krea-2-Turbo) for text-to-image and image-to-image, all backed by locally measured benchmark data.

![modes](https://img.shields.io/badge/modes-8-green) ![vram](https://img.shields.io/badge/VRAM-8GB%20OK-blue) ![comfyui](https://img.shields.io/badge/ComfyUI-0.33-orange)

---

## ✨ Features

| Mode | Description |
|---|---|
| 📝 T2VA | Text-to-video (with native synchronized audio) |
| 🖼️ I2VA | First-frame image-to-video, auto aspect matching |
| 🔄 FL2VA | First/last frame video |
| 🧩 Ref2VA | Multi-reference (≤9 images + ≤3 videos + ≤3 audios): identity / outfit / style editing |
| 🎬 MULTI | Multi-shot short film: storyboard → shot-by-shot generation (auto first-frame chaining) → one-click ffmpeg stitching (hard cut / crossfade) |
| ✨ PROMPT | Plain-language → H3 best-practice prompt optimizer (local rule engine, zero dependencies) |
| 🖼️ T2I / 🎨 I2I | Dedicated image backends: NoobAI-XL (SDXL), Krea-2-Turbo (NVFP4) and **Qwen-Image-Edit 2511 (GGUF)**, with negative prompt / denoise / speed LoRA |

**Highlights**
- Generation history (video/image filterable separately, persisted in localStorage)
- Built-in benchmark data (video 14 runs + image 10 runs, auto-switched by mode)
- One-click recommended presets (based on local measurements)
- Fully local, no cloud calls

---

## 🖥️ Hardware Requirements

**Tested platform**: RTX 5060 **8GB** · i5-14600KF · 32GB RAM · Windows 11 · ComfyUI 0.33.0 · torch 2.9.1+cu130

| Setup | Expected results |
|---|---|
| 8GB VRAM (baseline) | All video modes at 864×480; 5-sec × 8 steps ≈ 188 s per clip; images 14-38 s |
| 12GB+ VRAM | Larger canvas and longer clips possible |
| 32GB RAM (recommended) | Needed for model swapping |

---

## 🚀 Quick Start

```powershell
# 1. Setup environment (ComfyUI source + venv + torch cu130 + custom nodes)
powershell -ExecutionPolicy Bypass -File scripts\install.ps1

# 2. Download model weights (NoobAI/Krea auto-download; H3 weights via script guidance)
powershell -ExecutionPolicy Bypass -File scripts\download_models.ps1

# 3. Launch and open the panel
powershell -ExecutionPolicy Bypass -File scripts\launcher.ps1
# Browser: http://127.0.0.1:8188/h3-studio
```

### Model checklist (place under `models/` subfolders, filenames must match)

| File | Size | Purpose | License |
|---|---|---|---|
| `minimax_h3_fl2va_pruned_int8_convrot.safetensors` | 20.0GB | H3 text/first-last-frame video | H3 Community License |
| `minimax_h3_ref2va_pruned_int8_convrot.safetensors` | 20.0GB | H3 multi-reference / still channel | H3 Community License |
| `qwen3vl_32b_minimax_h3_nvfp4_awq.safetensors` | 15.0GB | H3 text encoder | H3 Community License |
| `minimax_h3_video_vae_fp16.safetensors` | 5.0GB | Video VAE | H3 Community License |
| `minimax_h3_audio_vae_fp32.safetensors` | 0.6GB | Audio VAE | H3 Community License |
| `NoobAI-XL-v1.0.safetensors` | 6.6GB | T2I / I2I (SDXL) | CC-BY-NC-SA-4.0 |
| `krea2_turbo_nvfp4.safetensors` | 7.3GB | Krea-2 image UNet | see Comfy-Org/Krea-2 |
| `qwen3vl_4b_fp8_scaled.safetensors` | 5.0GB | Krea-2 text encoder | see Comfy-Org/Krea-2 |
| `qwen_image_vae.safetensors` | 0.2GB | Krea-2 VAE | see Comfy-Org/Krea-2 |
| `krea2_style_reference.safetensors` | 0.4GB | Krea style-reference LoRA | see Comfy-Org/Krea-2 |
| `qwen-image-edit-2511-Q4_K_M.gguf` | 12.3GB | Qwen edit UNet (GGUF Q4) | Qwen community GGUF |
| `qwen_2.5_vl_7b_fp8_scaled.safetensors` | 8.7GB | Qwen text encoder | Comfy-Org / Qwen |
| `Qwen-Image-Lightning-8steps-V1.1-bf16.safetensors` | 0.8GB | Qwen 8-step speed LoRA | Qwen-Image-Lightning |

> ⚠️ **Weights are NOT distributed with this repo** — fetch them via `download_models.ps1` or from the original repos. Licenses and regional restrictions: see [NOTICE.md](NOTICE.md).

---

## 📊 Benchmarks (measured on RTX 5060 8GB)

### Video (H3, 864×480)

| Mode | 5s·8 steps | 10s·8 steps | 15s·8 steps | 15s·20 steps |
|---|---|---|---|---|
| T2VA | **188 s** | 543 s | 898 s | 2043 s (≈34 min) |
| I2VA | 188 s | 468 s | 985 s | — |
| FL2VA | 200 s | 513 s | 1078 s (≈18 min) | — |
| Ref2VA | 188 s | 468 s | 985 s | — |

> All times in **seconds**. VRAM peak 7.0-7.7GB · GPU load 86-97% · temp 66-70℃ · 20-step audio floor -17dB (8-step -51dB)

### Images (NoobAI / Krea, 1024²)

| Model | Params | Time | VRAM peak |
|---|---|---|---|
| NoobAI-XL | 20 steps·cfg5 | 14-18 s | 7.2GB |
| NoobAI-XL | img2img dn0.75 | 10 s | 6.9GB |
| Krea-2-Turbo | 4 steps·cfg1 | 16 s | 7.5GB |
| Krea-2-Turbo | 8 steps·cfg1 | 26 s | 7.4GB |
| Qwen-Edit 2511 | 8 steps·cfg1 (Lightning) | 80-95 s | 7.4GB |
| Qwen-Edit 2511 | 20 steps·cfg4 (standard) | 260 s | 7.4GB |

Full data: `benchmark/` (results.json + per-second telemetry CSVs + reproduction scripts)

---

## 🧭 Repository Layout

```
h3-studio/
├─ custom_nodes/h3-studio-web/    # Web panel (ComfyUI custom node, route /h3-studio)
├─ workflows/                     # Ready-to-use ComfyUI API workflow JSONs
├─ benchmark/                     # Benchmarks: video 14 runs / H3 still 9 runs / image 10 runs
│  ├─ bench_driver.py             #   video benchmark (4 modes × durations × steps + telemetry)
│  ├─ still/still_bench.py        #   H3 still benchmark
│  ├─ img/img_bench.py            #   NoobAI/Krea image benchmark
│  └─ img/mode_switch_test.js     #   panel UI regression test (stub DOM, no ComfyUI needed)
├─ scripts/
│  ├─ install.ps1                 # environment setup
│  ├─ download_models.ps1         # weight download
│  ├─ launcher.ps1 / stop.ps1     # start / stop
└─ docs/
   ├─ h3-prompt-library.md        # H3 prompt library (best-practice templates)
   ├─ vram-tuning.md              # 8GB VRAM tuning notes (pitfalls included)
   └─ image-model-research.md     # model selection research for 8GB GPUs
```

---

## 🔧 Dependencies

- [ComfyUI](https://github.com/comfyanonymous/ComfyUI) ≥ 0.33 (GPL-3.0)
- [comfyui-minimax-h3-audio-T8](https://github.com/T8mars/comfyui-minimax-h3-audio-T8) (H3 nodes)
- [ComfyUI-VideoHelperSuite](https://github.com/Kosinkadink/ComfyUI-VideoHelperSuite) (video output)
- [ComfyUI-KJNodes](https://github.com/kijai/ComfyUI-KJNodes)
- Python 3.10+ · torch ≥2.9 (cu130) · ffmpeg

---

## 📄 License

- **Repo code**: GPL-3.0 (consistent with ComfyUI), see [LICENSE](LICENSE)
- **Model weights**: each has its own license, see [NOTICE.md](NOTICE.md) — MiniMax H3 official Community License **excludes US/EU/UK/South Korea etc.**; NoobAI-XL is CC-BY-NC-SA-4.0 (non-commercial). Verify your region and use case before use.

---

## ⚠️ Disclaimer

This repository is an open-source **tool** that provides local generation capabilities only and includes **no content moderation, filtering, or blocking**. You are **solely responsible** for the content you generate with it, including but not limited to images, videos, audio, and text:

- Ensure your usage complies with your local laws, the model weight licenses (see [NOTICE.md](NOTICE.md)), and applicable platform terms of service;
- Generated content may be inaccurate, inappropriate, or misleading; do not use it for illegal, infringing, fraudulent, hateful, or harmful purposes;
- The authors and contributors are not liable for any direct or indirect damages, legal consequences, or third-party claims arising from the use, modification, or distribution of this project;
- This statement is not legal advice.

By installing or using this project, you acknowledge that you have read and agree to these terms.

---

## 🙏 Acknowledgements

- The MiniMax team and the H3 open-source community
- [T8mars](https://github.com/T8mars) and the ComfyUI ecosystem node authors
- All open-source authors dedicated to low-VRAM local AI deployment and optimization
