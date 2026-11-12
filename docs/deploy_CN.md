# 部署 E2E 版

[English](deploy.md)

E2E 版只需要**一张 80 GB 显卡**。权重：[魔搭](https://www.modelscope.cn/models/AdventistsAI/Sophon-Realtime-32B-E2E) · [HF](https://huggingface.co/adventists-ai/Sophon-Realtime-32B-E2E)。

它由同一张显卡上的三个本地服务组成：

| 服务 | 作用 | 默认端口 |
|---|---|---|
| 思考器 | 听用户说话，判断用户是否说完，写回复（带声音标签）。vLLM 0.29 + 回复 LoRA | 8300 |
| 发声引擎 | 回复边写边说：说话头（约 3.5 亿参数）→ 向量帧 → 解码器 → 24 kHz 音频。所有对话在同一个循环里合批处理 | 8120 |
| 网关 | WebSocket 接口和网页 demo。接收麦克风流，做话轮判断，播放回复，处理打断 | 8000 |

## 环境要求

- Linux，NVIDIA 驱动 580 及以上（安装的 PyTorch 是 CUDA 13 版本），Python 3.10+。
- **一张 80 GB 显卡**（H100 / A100 80G / H800 等），实际占用显存约 70 GB。
- CUDA MPS（`nvidia-cuda-mps-control`，NVIDIA 驱动自带）。`scripts/start.sh` 会为这张卡单独启动一个 MPS 守护进程，让思考器和发声引擎同时使用显卡。不用 MPS 也能跑，但两个进程只能轮流用显卡：单用户首包会从约 0.25 秒变成约 0.6 秒，并发能力也会下降。
- 权重约需 75 GB 磁盘。

## 安装

```bash
git clone https://github.com/adventists-ai/sophon-realtime
cd sophon-realtime
bash scripts/install.sh          # 建两个虚拟环境，并从魔搭下载模型
```

- 国内可以加 PyPI 镜像：`PIP_INDEX_URL=https://mirrors.cloud.tencent.com/pypi/simple bash scripts/install.sh`。
- 已经下载好模型的话：`SKIP_DOWNLOAD=1 MODEL_DIR=/path/to/Sophon-Realtime-32B-E2E bash scripts/install.sh`。
- 从双卡版本（权重 `v1.1.0` 及更早）升级：需要重新下载权重。新权重多了 `talker220/` 目录，不再需要 `talker/`。

## 启动

```bash
SOPHON_MODEL_DIR=$PWD/Sophon-Realtime-32B-E2E GPU=0 bash scripts/start.sh
```

第一次启动约需 5 分钟（加载权重，发声引擎捕获 CUDA graph）。启动后打开 `http://<服务器>:8000/` 就能直接对话。建议戴耳机，免得模型听到自己的声音。

`bash scripts/stop.sh` 停止全部服务（包括它启动的 MPS 守护进程），日志在 `logs/` 下。

| 变量 | 默认值 | 说明 |
|---|---|---|
| `GPU` | 0 | 用哪张显卡 |
| `PORT` | 8000 | 网关 / 网页 demo |
| `SLOTS` | 16 | 发声引擎同时为多少路对话发声 |
| `MPS` | 1 | 设为 0 则不使用 CUDA MPS |
| `THINKER_MEM` | 0.55 | 分给思考器的显存比例 |
| `SOPHON_REPLY_LORA` | `$SOPHON_MODEL_DIR/adapters/tag` | 回复 LoRA，例如你自己[微调](../finetune/README_CN.md)出来的 |
| `LORA_RANK` | 16 | 回复 LoRA 的最大秩 |
| `S220_NT` | 2 | 每块音频的解码步数；设为 4 音质略干净一些，解码耗时约为两倍 |

## 性能（单张 H100 80 GB，全新安装后实测）

语音提问进、语音回答出，全链路（思考器 + 发声引擎 + 网关都在同一张卡上）。首包指从发出请求到收到第一块音频的时间。

| 10 秒内到达的用户数 | 首包 中位数 / P90 | 播放落后超过 0.3 秒的回复数 |
|---|---|---|
| 1 | 0.25 秒 | 0 |
| 8 | 0.44 / 0.77 秒 | 0 / 8 |
| **16** | **0.44 / 0.56 秒** | **0 / 16** |
| 24 | 0.58 / 0.94 秒 | 7 / 24 |
| 32 | 0.67 / 0.80 秒 | 23 / 32 |

持续负载：16 路对话同一时刻开始、每路连续 5 轮（共 80 条回复），首包中位数 0.51 秒 / P90 0.62 秒，80 条里有 10 条在某一时刻播放落后超过 0.3 秒（最多 0.59 秒）。同样方式 8 路：0.40 / 0.48 秒，没有落后。

**建议每张卡最多 16 路。** 需要更多并发时，每张卡起一个实例（`GPU=1 PORT=8001 …`），前面加负载均衡。

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

## 声音标签

这些标签会被说话头演出来，不会念出来。第一行的标签思考器自己会写；其余的只要出现在回复里就会被演出来，例如来自你自己微调的回复 LoRA，或者你直接发给发声引擎（`/tts`）的文字。

| 标签 | 说明 |
|---|---|
| `[laughter]` `[cough]` `[sigh]` `[breath]` | 在句子的这个位置发出对应的声音 |
| `[cry]` `[clear]` `[gasp]` | 抽泣、清嗓子、倒吸一口气（可以用，尚未做评测） |
| `<strong>词</strong>` | 重读这个词 |
| `<laughter>几个词</laughter>` | 边笑边说这几个词 |

## 模型仓库里的文件

| 路径 | 说明 |
|---|---|
| `base/` | 思考器的 32B 权重 |
| `adapters/tag/` | 写声音标签的回复 LoRA |
| `talker220/` | 说话头：权重、文字嵌入表、分词器 |
| `e2/` | 解码器和 HiFT 声码器 |
| `voices/` | 默认音色 |
| `thinker/`、`config.json`、`talker220/config.json` | 只给 [vLLM-Omni 部署方式](../e2e/README_CN.md)用：已合并回复 LoRA 的思考器，FP8（约 36 GB）。`scripts/install.sh` 不会下载 `thinker/` |

## 这一版的限制

- 只有一个内置音色，这一版不支持音色克隆（需要克隆请用 [Tag](../tag/README_CN.md) 或 [Flash](../flash/README_CN.md) 版）。
- 回复用中文或英文。
- 单条回复最长约 4.6 分钟语音（文字约 960 个 token）；超出时这条回复会在该处正常结束，不影响其他对话。
- 句尾的声音事件最长约 1.6 秒。
