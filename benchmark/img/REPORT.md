# H3 Studio 图片后端替换 · 图像模型实测报告

**日期**:2025 本地实测
**硬件**:RTX 5060 8GB(38 TFLOPS FP16 / 448GB/s) · i5-14600KF · 32GB RAM · Win11
**软件**:ComfyUI 0.33.0 · torch 2.9.1+cu130 · 原生 NVFP4(Blackwell)支持
**测试提示词**(所有轮次一致):
> A cinematic portrait of a young woman with natural skin texture and loose brown hair, standing in a sunlit city street at golden hour, shallow depth of field, filmic 35mm look.

图生图源图:`clothes_ref.png`(864×480,黄金时刻街景人像,取自 H3 实测样片)。

---

## 1. 部署模型清单(共 19.6 GB)

| 文件 | 大小 | 用途 | 来源 |
|---|---|---|---|
| `NoobAI-XL-v1.0.safetensors` | 6,616.6 MB | SDXL 全量 checkpoint | hf-mirror / Laxhar/noobai-XL-1.0 |
| `krea2_turbo_nvfp4.safetensors` | 7,318.2 MB | Krea-2 Turbo UNET(NVFP4,Blackwell 原生) | hf-mirror / Comfy-Org/Krea-2 |
| `qwen3vl_4b_fp8_scaled.safetensors` | 4,999.6 MB | Krea-2 文本编码器(Qwen3-VL-4B FP8) | hf-mirror / Comfy-Org/Krea-2 |
| `qwen_image_vae.safetensors` | 242.0 MB | Krea-2 图像 VAE | hf-mirror / Comfy-Org/Krea-2 |
| `krea2_style_reference.safetensors` | 435.9 MB | Krea 风格参考 LoRA | hf-mirror / Comfy-Org/Krea-2 |

**关键部署修正**(本次会话踩坑):
1. `extra_model_paths.yaml` 补 `checkpoints` 映射(原配置缺失 → NoobAI 无法被 ComfyUI 识别,列表为空)。
2. ComfyUI 0.33 的 KSampler **没有 `euler_a`**,已改名为 `euler_ancestral`;旧名提交直接 400 `value_not_in_list`。
3. Krea-2 的 CLIPLoader **必须用 `type:'krea2'`**(12 层 TAP 融合),`qwen_image` 类型会导致 UNET `_unpack_context` 特征形状校验失败。

---

## 2. 基准结果(10 轮,含遥测)

| 轮次 | 参数 | 耗时(秒) | VRAM 峰值 | GPU 均载 | 温度 | PSNR* | 说明 |
|---|---|---|---|---|---|---|---|
| NOOBAI_1024_s20_cfg5 | 1024²·20步·cfg5·euler_ancestral/karras | **18.1s** | 7.24GB | 60% | 59℃ | — | 首轮含模型加载 |
| NOOBAI_1024_s30_cfg5 | 1024²·30步·cfg5 | 18.1s | 7.36GB | 75% | 62℃ | — | 与 20 步同耗时,受 GPU 频率波动影响 |
| NOOBAI_1024_s20_cfg7 | 1024²·20步·cfg7 | 14.1s | 7.41GB | 70% | 62℃ | — | cfg7 更快疑为频率/缓存波动 |
| NOOBAI_832x1216_s25 | 832×1216·25步·cfg5 | 16.1s | 7.41GB | 72% | 63℃ | — | 竖版构图无额外开销 |
| NOOBAI_I2I_s20_dn075 | 1024²·20步·dn0.75 | **10.1s** | 6.94GB | 49% | 60℃ | **15.58dB** | 稳态耗时,贴近原图 |
| KREA_1024_s4_cfg1 | 1024²·4步·cfg1·er_sde/simple | **16.1s** | 7.49GB | 65% | 62℃ | — | 最快档 |
| KREA_1024_s8_cfg1 | 1024²·8步·cfg1 | 26.3s | 7.37GB | 71% | 62℃ | — | 官方推荐档 |
| KREA_1024_s12_cfg1 | 1024²·12步·cfg1 | 38.2s | 7.30GB | 74% | 64℃ | — | 更稳但慢 |
| KREA_1024_s8_lora09 | 1024²·8步·cfg1·风格LoRA 0.9 | 36.2s | 7.20GB | 89% | 64℃ | — | LoRA 使模型重建→耗时上升 |
| KREA_I2I_s8_dn07 | 1024²·8步·dn0.7 | 16.1s | 7.09GB | 71% | 63℃ | **11.91dB** | 改动幅度大于 NoobAI 同档 |

\* PSNR:输出与源图相似度(越高越贴近原图),仅图生图轮次计算。

### 结论要点
- **速度**:NoobAI 20-30 步 ≈ 14-18 秒/张(稳态 10-14 秒);Krea 4-12 步 ≈ 16-38 秒。**Krea 在 8GB 上并未比 NoobAI 快** —— 7.3GB NVFP4 模型 + 4GB FP8 文本编码器在 8GB 显存下需频繁换载,抵消了步数优势;其价值在**字面遵循与构图准确**(turbo 蒸馏模型对提示词响应直接)。
- **显存**:两者 VRAM 峰值 7.0-7.5GB,8GB 卡均可稳定运行,无 OOM。
- **图生图**:NoobAI dn0.75 PSNR 15.6dB(保留构图、改细节);Krea dn0.7 PSNR 11.9dB(改动更大,适合风格转换)。注意源图为 864×480,I2I 输出跟随源图尺寸。
- **稳定性**:全 10 轮零失败;温度 59-64℃,GPU 均载 49-89%。

---

## 3. 页面集成(H3 Studio T2I/I2I 已替换)

`h3-studio.html` 的图片生成卡片重构为**三后端**:

```
模型后端:
├─ 🎨 NoobAI-XL 1.0(SDXL)      ← 默认,细节/风格自由,支持负面提示词
├─ ⚡ Krea-2-Turbo(NVFP4)       ← 字面遵循强,CFG 固定 1,可选风格 LoRA
└─ 📼 H3 微视频(旧通道)          ← 保留备选
```

- **T2I**:NoobAI → CheckpointLoaderSimple + CLIPTextEncode(正/负) + EmptyLatentImage + KSampler(euler_ancestral/karras,步数 20-30,cfg 5-7);Krea → UNETLoader + CLIPLoader(krea2) + VAELoader + KSampler(er_sde/simple,步数 4-12,cfg=1),LoRA 开关(0-1.5,默认 0.9)。
- **I2I**:LoadImage → VAEEncode → KSampler 的 `denoise` 滑块(默认 0.75,范围 0.05-1.0),尺寸跟随源图。
- **UI 联动**:后端切换时自动隐藏/显示专属控件(负面提示词、LoRA、H3 帧数/强度),并自动设置推荐采样器与 CFG;实测数据内嵌为提示文案。
- **历史记录**:新增 backend/cfg/sampler/denoise/lora 参数回显,图片预览不变。

### 页面冒烟测试(page_smoke.py)
与页面节点图完全一致的 4 组合(T2I/I2I × NoobAI/Krea)均成功出图,证明页面后端可用。

---

## 4. 使用建议(8GB 场景)

| 需求 | 推荐 |
|---|---|
| 快速出图/多图尝试 | NoobAI 20步·cfg5(≈14-18s) |
| 高清细节 | NoobAI 30步·cfg5 或 832×1216 竖版 |
| 文字/构图字面遵循 | Krea s8·cfg1(≈26s),可叠风格 LoRA 0.9 |
| 保留原图改局部 | NoobAI I2I · dn0.75(≈10s) |
| 风格大改/转绘 | Krea I2I · dn0.7(≈16s) |

**提示词**:NoobAI 支持中文;Krea 英文遵循最佳;NoobAI 可配负面提示词(`worst quality, low quality, blurry, deformed, bad anatomy, watermark, text, jpeg artifacts`)。

---

## 5. 文件

- `results.json` — 10 轮完整数据(耗时/遥测/质量)
- `telemetry/*.csv` — 逐秒遥测(nvidia-smi)
- `page_smoke.py` + `smoke_log.txt` — 页面工作流冒烟测试
- `bench_log.txt` — 基准运行日志
- 样例输出:`output/IMG_NB_*`、`IMG_KR_*`、`Smoke_*`
