# 模型说明与安装方案（MODELS）

本工具依赖 **两套模型栈**，都跑在同一个 ComfyUI 实例里：

| 模型栈 | 用途 | 主链路环节 |
|---|---|---|
| **MiniMax H3** | 视频（音画同生，原生立体声） | 第 7 步提交出片 |
| **Z-Image-Turbo** | 图片（文生图） | 第 5 步参考资产（锚点图/场景图/分镜图） |

> 推荐 GPU：NVIDIA 24GB 显存（RTX 3090/4090 实测可跑）；显存更小请用 0.4MP 预览档 + 云端生图。

---

## 1. 安装 ComfyUI

```bash
# 方式一：git（推荐，便于更新）
git clone https://github.com/comfyanonymous/ComfyUI
cd ComfyUI
pip install -r requirements.txt

# 方式二：Windows 便携包
# 下载 ComfyUI_windows_portable_nvidia.7z 解压即可
```

**启动参数（重要）**：必须加 `--cuda-malloc` 启用 CUDA caching allocator，否则批量生成易 OOM：

```bat
python main.py --cuda-malloc
```

默认地址 `http://127.0.0.1:8188`，与 `config.json -> comfyui.server` 对应。

---

## 2. 安装 H3 自定义节点（必须）

ComfyUI 内 Manager 搜索 **MiniMax-H3**，或手动：

```bash
cd ComfyUI/custom_nodes
git clone https://github.com/Comfy-Org/MiniMax-H3
pip install -r MiniMax-H3/requirements.txt
```

提供节点：`MiniMaxH3ReferenceToVideo`（R2V）/ `MiniMaxH3ImageToVideo`（I2V）/ `MiniMaxH3TurboLoRA` / `MiniMaxH3MemoryEfficientSageAttentionPatch`（后两个为 ≤8 步自动注入的加速节点）。

---

## 3. MiniMax H3 视频模型

来源仓库：<https://huggingface.co/Comfy-Org/MiniMax-H3>
按**目录对应关系**下载到 ComfyUI `models/` 下对应子目录：

| 文件 | 放置目录 | 用途 |
|---|---|---|
| `minimax_h3_fl2va_pruned_int8_convrot.safetensors` | `diffusion_models/` | T2V / I2V 主权重（FL2VA） |
| `minimax_h3_ref2va_pruned_int8_convrot.safetensors` | `diffusion_models/` | R2V 主权重（Ref2VA，多参考锁身份） |
| `qwen3vl_32b_minimax_h3_nvfp4_awq.safetensors` | `text_encoders/` | 文本编码器（Qwen3-VL 32B，官方版） |
| `minimax_h3_video_vae_fp16.safetensors` | `vae/` | 视频 VAE |
| `minimax_h3_audio_vae_fp32.safetensors` | `vae/` | 音频 VAE（原生立体声） |
| `minimax_h3_turbo_v4_step600_ema.safetensors` | `loras/` | Turbo v4 加速 LoRA（4/6/8 步用） |

一键下载（huggingface-cli，注意目录映射）：

```bash
pip install -U "huggingface_hub[cli]"
export HF_ENDPOINT=https://hf-mirror.com          # 国内加速可选
huggingface-cli download Comfy-Org/MiniMax-H3 \
  --local-dir ComfyUI/models/h3_tmp
# 下载后把文件按上表移到 diffusion_models/ text_encoders/ vae/ loras/
```

> 下载受代理影响时，确认系统代理端口设置正确再执行；中断重跑会续传。

### 模型约束（实测经验，务必遵守）

- **R2V 步数 ≥6**：turbo v4 官方推荐区间 6-8 步；低于 6 步音频细节不足（声音发糊）、大动态镜头拖影
- **步数 >8 自动跳过 turbo LoRA 注入**（高步数走原生采样，质量档与加速档自动区分）
- **分辨率由任务 `mp` 参数控制**，默认 0.4MP（480×864，9:16 竖版）
- **24GB 显存不要超过 1.0MP**：更高分辨率触发权重 offload，速度显著下降
- **R2V 与 FL2VA 是两套权重**：提交 R2V 时系统自动检测服务器是否加载 ref2va 权重，缺失则回退 FL2VA 并提示（身份锁定变弱）

### 可选：未审查 CLIP（个人本地使用）

| 文件 | 放置目录 |
|---|---|
| `qwen3vl_32b_h3_ultra_uncensored_heretic_int8_convrot.safetensors` | `text_encoders/` |
| `qwen3vl_32b_h3_generation_tail_50_63_int8_convrot.safetensors` | `text_encoders/` |

- 代价：约 **31.5GB 磁盘 / 24.7GiB 显存**，RTX 3090 上因 offload 明显变慢
- 替换后同步修改 `config.json -> models.r2v.clip`
- **不要**把未审查模型名写进提交到开源仓库的 `config.example.json`

---

## 4. Z-Image-Turbo 文生图模型

来源：<https://huggingface.co/Comfy-Org/Z-Image-Turbo>（与视频共用同一 ComfyUI 实例）

| 文件 | 放置目录 | 用途 |
|---|---|---|
| `z_image_turbo_bf16.safetensors` | `diffusion_models/` | 生图主模型（约 19.7GB） |
| `qwen_3_4b.safetensors` | `text_encoders/` | 文本编码器（CLIPLoader type=lumina2） |
| `ae.safetensors` | `vae/` | VAE |

采样配置（内置工作流已固化）：UNETLoader → ModelSamplingAuraFlow(shift=3) → KSampler（8 步，cfg=1，res_multistep/simple）→ VAEDecode → SaveImage。

> **显存注意**：首次生图需把 19.7GB 主模型全部载入显存；24GB 卡可跑但会占满。视频与生图混跑时，控制台提交批量任务前会**自动卸载 Ollama 模型并清理 ComfyUI 显存缓存**，防止 OOM。

---

## 5. 语言模型（LLM，剧本/提示词扩写）

二选一，`config.json -> llm.provider` 切换（主端点失败自动降级另一侧）：

| 方案 | 配置 | 说明 |
|---|---|---|
| 本地 | `local.url=http://127.0.0.1:1234` | LM Studio / Ollama，OpenAI 兼容；加载一个指令模型即可 |
| 云端 | `cloud.base_url / api_key / model` | OpenAI 兼容（DeepSeek/通义/OpenAI 等）；非 OpenAI 格式用 `provider_type: claude / dashscope` 适配器 |

本地不可用且云端未启用时，控制台自动回退内置规则扩写（能跑，效果弱）。

## 6. 视觉质检模型（可选）

`config.json -> vision`：任意 OpenAI 兼容视觉服务（如通义 qwen-vl），用于参考图自动质检（人数/服装/穿帮）。不配置则跳过质检。

---

## 7. 安装验证

```bash
python scripts/check_env.py       # 逐项检查 Python/ffmpeg/config/远程服务/模型
```

或在控制台「⚙️ 设置 → 连接测试」：绿灯 = ComfyUI 在线。
生图检测：进入第 5 步「参考资产」，顶部自动显示「检测本地生图服务」结果。
