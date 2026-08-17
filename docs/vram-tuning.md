# MiniMax H3 8GB 显存部署与调优实战

> 本文所有结论来自 RTX 5060 8GB + 32GB RAM + i5-14600KF + Win11 的实测(2026 实测,ComfyUI 0.33.0 + torch 2.9.1+cu130)。每项均附遥测数据来源(benchmark/ 目录)。

## 1. 为什么 33B 模型能进 8GB

MiniMax H3 是 33B 全模态(视频+音频)扩散模型,原生需要 A100/H100 级显存。8GB 可行的关键:

| 手段 | 作用 |
|---|---|
| **pruned int8 转换版权重**(FL2VA/Ref2VA ~20GB 文件) | 权重压缩,UNet 可加载 |
| **NVFP4 量化文本编码器**(qwen3vl_32b_nvfp4_awq) | Qwen3-VL-32B 编码器从 60GB+ 降到 15GB |
| **ComfyUI 动态显存** | 模型/编码器/VAE 按需换入换出 VRAM |
| **--cache-none --reserve-vram 1.0 --disable-pinned-memory** | 避免常驻缓存与锁页内存,减少峰值 |
| **画布限制** | 视频默认 864×480(2.0MP 内),生图 ≤2.0MP |

启动参数(见 scripts/launcher.ps1):

```
python main.py --enable-dynamic-vram --fast-disk --cache-none \
  --reserve-vram 1.0 --disable-pinned-memory --port 8188
```

## 2. 帧数网格:必须遵守 17n+5

H3 训练帧网格:`5, 22, 39, 56, 73, 90, 107, 124, 141, ..., 243, 362`

- 时长档位:5 秒 = **124 帧**,10 秒 = **243 帧**,15 秒 = **362 帧**
- 非网格帧数会被节点自动吸附(align_frame_count),但主动选择网格帧避免意外
- 生图通道帧数档位:22 帧(短微视频)/ 5 帧(最快)/ 124 帧(最稳)

显存占用与帧数近似线性,`video_latent_t` 经验公式:

```
fc <= 5   → t = 2
否则       → t = ((fc-5)//17)*5 + 2
```

## 3. 速度基准(864×480,遥测见 benchmark/results.json)

| 模式 | 5s·8步 | 10s·8步 | 15s·8步 | 15s·20步 |
|---|---|---|---|---|
| T2VA | 188s | 543s | 898s | 2043s |
| I2VA | 188s | 468s | 985s | — |
| FL2VA | 200s | 513s | 1078s | — |
| Ref2VA | 188s | 468s | 985s | — |

- VRAM 峰值 7.0-7.7GB,GPU 均载 86-97%,温度 66-70℃
- **四模式同档位几乎同速**(瓶颈在采样步数)
- **20 步音频明显更饱满**(约 -17dB vs 8 步 -51dB 底噪),视频对白/音乐场景用 20 步
- **15 秒建议拆 5 秒×3 拼接**:三段 5s(564s)比一段 15s(898s)快且易控

## 4. 生图通道(H3 Still)

H3 生成"静态图"实际是微视频取帧:

| 配置 | 耗时 |
|---|---|
| T2I 22帧·8步 1024² | 87s |
| T2I 5帧·8步 | 47s |
| T2I 22帧·20步 | 314s |
| I2I 22帧·8步 | ~90s |

- **推荐 22 帧档**(稳且快);124 帧最稳但慢 3 倍
- 图生图用 `reference_strength`:0.99 → 相似度 10.5dB;0.80 → 7.75dB(作用温和,**加步数比调强度更有效**)
- 2.0MP 画布上限,尺寸需 32 的倍数
- 注意:此通道需要 **Ref2VA 权重**(still 条件节点走 Ref2VA)

## 5. 换装/换人实测(Ref2VA)

- **视频参考在 8GB 上不可行**:源视频(5s)+ Ref2VA 条件编码 >20 分钟且吃满显存 → 放弃
- **图片参考是正解**:单张参考图 189s 出 5s 视频,身份/服装保持可用
- 提示词用 `subject_definitions:` + `detailed_description:` 结构(见 docs/h3-prompt-library.md)

## 6. 8GB 上值得注意的坑(全部踩过)

| 坑 | 现象 | 解法 |
|---|---|---|
| `euler_a` 不存在 | KSampler 400 `value_not_in_list` | ComfyUI 0.33 已改名 **`euler_ancestral`** |
| Krea-2 CLIP 类型 | UNET `_unpack_context` 特征形状校验失败 | CLIPLoader 必须用 **`type:'krea2'`**(12 层 TAP),不能用 `qwen_image` |
| extra_model_paths 缺 checkpoints | NoobAI 不出现在 CheckpointLoaderSimple 列表 | yaml 中显式加 `checkpoints:` 映射 |
| uv venv 双进程 | 启动脚本误判"启动失败" | 以 **8188 端口就绪**为准,不要信 wrapper 进程退出码 |
| Ref2VA 视频参考 OOM/超时 | >20 分钟不出结果 | 改用图片参考 |
| H3 生图 400 | `audio_vae` 指向不存在的节点 | 补音频 VAELoader 节点(audio_target=generate_and_discard 也要接) |
| VHS 视频参考读取失败 | 只读 input 目录 | 先把源视频复制到 ComfyUI/input/ 再引用 |

## 7. 图像模型替换(NoobAI-XL / Krea-2-Turbo)

8GB 上 H3 生图太慢(~90s),面板已内置专职图像模型后端:

| 模型 | 参数 | 耗时 | VRAM | 特点 |
|---|---|---|---|---|
| NoobAI-XL 1.0(SDXL) | 20步·cfg5·euler_ancestral/karras | 14-18s | 7.2-7.4GB | 无内容过滤,风格自由,中文可用 |
| Krea-2-Turbo NVFP4 | 8步·cfg1·er_sde/simple | 26s | 7.4GB | 字面/构图遵循强,Blackwell 原生 |

- Krea 在 8GB 上不比 NoobAI 快(7.3GB NVFP4 + 4GB FP8 编码器频繁换载),选它因为提示词遵循
- Krea 依赖 ComfyUI ≥0.33(原生 nvfp4 ops)与 torch ≥2.9 + cu130
- 图生图:NoobAI dn0.75 ≈ 10s(PSNR 15.6dB,保留构图);Krea dn0.7 改动更大
