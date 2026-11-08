# 部署 E2E 版（预览）

[English](deploy.md)

> **预览版。** E2E 版是研究预览；新版本正在测试，准备好后发布权重。生产环境请用 [Tag](../tag/README_CN.md) 或 [Flash](../flash/README_CN.md) 版：一张显卡、一条命令。

Sophon-Realtime v1 由三个本地服务组成：

| 服务 | 作用 | 默认端口 | 显卡 |
|---|---|---|---|
| 思考器 | 听用户说话，判断用户是否说完，写回复（带声音标签）。vLLM 0.29 + 回复 LoRA | 8300 | 1 张 80 GB |
| 发声引擎 | 回复边写边说：说话头 → 向量帧 → E2 → 24 kHz 音频 | 8120 | 1 张 80 GB |
| 网关 | WebSocket 接口和网页 demo。接收麦克风流，做话轮判断，播放回复，处理打断 | 8000 | – |

## 环境要求

- Linux，NVIDIA 驱动 580 及以上（安装的 PyTorch 是 CUDA 13 版本），Python 3.10+。
- **两张 80 GB 显卡**（H100 / A100 80G / H800 等）：思考器一张，发声引擎一张。
- 权重约需 80 GB 磁盘。

## 安装

```bash
git clone https://github.com/adventists-ai/sophon-realtime
cd sophon-realtime
bash scripts/install.sh          # 建两个虚拟环境，并从魔搭下载模型
```

- 国内可以加 PyPI 镜像：`PIP_INDEX_URL=https://mirrors.cloud.tencent.com/pypi/simple bash scripts/install.sh`。
- 已经下载好模型的话：`SKIP_DOWNLOAD=1 MODEL_DIR=/path/to/Sophon-Realtime-32B-E2E bash scripts/install.sh`。

## 启动

```bash
SOPHON_MODEL_DIR=$PWD/Sophon-Realtime-32B-E2E THINKER_GPU=0 TALKER_GPU=1 bash scripts/start.sh
```

第一次启动需要 3–5 分钟（加载权重，发声引擎捕获 CUDA graph）。启动后打开 `http://<服务器>:8000/` 就能直接对话。建议戴耳机，免得模型听到自己的声音。

`bash scripts/stop.sh` 停止全部服务，日志在 `logs/` 下。

| 变量 | 默认值 | 说明 |
|---|---|---|
| `PORT` | 8000 | 网关 / 网页 demo |
| `THINKER_GPU`、`TALKER_GPU` | 0、1 | 用哪两张卡 |
| `SOPHON_REPLY_LORA` | `$SOPHON_MODEL_DIR/adapters/tag` | 回复 LoRA，例如你自己[微调](../finetune/README_CN.md)出来的 |
| `LORA_RANK` | 16 | 回复 LoRA 的最大秩 |
| `T32_SLOTS` | 8 | 发声引擎同时保持的对话数 |

## WebSocket 接口（`/ws`）

流式全双工（网页 demo 用的就是这种方式）：

1. 先发 `{"type": "config", "lang": "zh" | "en", "history": true}`。
2. 用二进制帧持续发送麦克风音频：16 kHz 单声道 PCM16，每块大小不限（demo 每块 512 个采样点）。
3. 会收到以下消息：
   - `{"type": "turn_commit", ...}`：模型判断你说完了，开始回答；
   - `{"type": "text", "delta": "..."}`：回复文字，其中包含 `[laughter]` 这类声音标签（标签会被演出来，不会念出来）；
   - 二进制帧：回复音频，24 kHz 单声道 PCM16；
   - `{"type": "barge_in"}`：你开口打断了，客户端应停止播放；
   - 先收到 `{"type": "metrics", ...}`，最后是 `{"type": "done"}`。

单轮模式（测试和跑分用，一次发一整句）：

```json
{"type": "turn", "audio_b64": "<wav，采样率不限>", "lang": "zh"}
```

回复的返回方式与流式相同（文字、音频、metrics、done）。

## 模型仓库里的文件

| 路径 | 说明 |
|---|---|
| `base/` | 共用的 32B 权重（思考器，也是说话头的主干） |
| `adapters/tag/` | 写声音标签（`[laughter]`、`[cough]`、`<strong>…</strong>` 等）的回复 LoRA |
| `talker/` | 说话头的 LoRA 和各个头 |
| `e2/` | E2 解码器和 HiFT 声码器 |
| `voices/` | 默认音色 |

## 这一版的限制

- 只有一个内置音色，暂不支持自定义音色。
- 每套部署需要两张显卡；保证完整音质时，可同时支持几路对话。
- 回复用中文或英文（思考器能听懂更多语言）。
