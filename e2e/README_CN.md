# Sophon-Realtime E2E 版的 vLLM-Omni 部署：一张卡，一条命令

[English](README.md)

把 Sophon-Realtime 的 E2E 版作为**一个 vLLM-Omni 模型**跑在一张 80 GB 显卡上，命令、接口和客户端与 [Tag](../tag/README_CN.md)、
[Flash](../flash/README_CN.md) 相同。它听你说话，写出可能带声音标签的回复（`[laughter]`、`[cough]`、`[sigh]`、`[breath]`、
`<strong>…</strong>`、`<laughter>…</laughter>`），边写边说。标签会被演出来，不会被念出来，文字流里也会去掉。

这是 E2E 的第二种部署方式。第一种是自研引擎（[docs/deploy_CN.md](../docs/deploy_CN.md)），速度略快（见下表）。两种方式用的是同一套
说话头和解码器权重，声音相同。

| | |
|---|---|
| 权重 | [魔搭](https://www.modelscope.cn/models/AdventistsAI/Sophon-Realtime-32B-E2E) · [Hugging Face](https://huggingface.co/adventists-ai/Sophon-Realtime-32B-E2E)（`thinker/`、`talker220/`、`e2/`、`voices/`、`config.json`） |
| 显卡 | 一张 H100 级的 80 GB 显卡，每个实例约 67 GB。其他显卡见[其他显卡](#其他显卡) |
| 接口 | `ws://HOST:PORT/v1/realtime`（全双工：话轮判断、打断）· `POST /v1/chat/completions`（语音进 → 文字 + 语音流） |

## 快速开始

```bash
git clone https://github.com/adventists-ai/sophon-realtime && cd sophon-realtime/e2e
bash install.sh                 # Python 3.12 环境、vLLM 0.30、vLLM-Omni 0.30、插件、torch 2.14.1，然后把权重下载到 ./model（约 41 GB）
GPU=0 PORT=8000 bash start.sh   # H100 上约 5 分钟（第一次启动要编译计算核，会多几分钟）；预热完才会打印 READY
python client_example.py --wav my_question.wav --lang zh
bash stop.sh
```

- 国内镜像：`PIP_INDEX=https://mirrors.aliyun.com/pypi/simple bash install.sh`。
- 权重已经下载好：`SKIP_DOWNLOAD=1 bash install.sh`，然后 `MODEL_DIR=/path/to/Sophon-Realtime-32B-E2E bash start.sh`。
  模型目录里需要 `thinker/`、`talker220/`、`e2/`、`voices/` 和 `config.json`；`base/` 和 `adapters/` 只有自研引擎用。
- 请保留整个仓库：插件要用到 `../sophon_expressive` 里的引擎代码。
- `install.sh` 特意在 vLLM 之后再装 torch 2.14.1。用旧版 torch 时，发声的两段会多占约 50 GB 显存。
  这样装之后，启动日志里会有一条 `vllm.third_party.deep_gemm` 导入失败的警告；这个模块本模型用不到。
- 一个内置音色（`chelsie`），支持中文和英文。需要声音克隆请用 Tag 或 Flash。

## 性能（单张 H100 80 GB，实测）

语音提问进、语音回答出，走 `/v1/chat/completions`，用户在 10 秒内陆续到达。

| 并发路数 | 首包 中位数 / P90 | 播放落后超过 0.3 秒的回复 | 对比：自研引擎 |
|---|---|---|---|
| 1 | 约 0.35 秒 | 0 | 0.25 秒 |
| 8 | 0.40–0.45 / 0.84–0.95 秒 | 0/8 | 0.44 / 0.77 秒，0/8 |
| **16** | **0.58–0.65 / 0.71–0.87 秒** | 0–2/16（最多落后 0.4 秒） | 0.44 / 0.56 秒，0/16 |
| 24 | 0.79–0.88 / 1.7–2.8 秒 | 1–3/24 | 0.58 / 0.94 秒，7/24 |
| 16 路 × 每路 5 轮 | 0.64 / 0.84–0.91 秒 | 0–1/80 | 0.51 / 0.62 秒，10/80 |

- **建议每张卡最多 16 路并发。**
- 全双工（`/v1/realtime`）：从你说完到听到第一声，中位数约 0.45 秒。
- 非语言声音：说话头的输出与自研引擎逐位相同，所以沿用它的 NVV-SuperBench 成绩（英文 0.75 / 中文 0.85）。
- 一条回复最多说约 2 到 2.5 分钟，到了就在句末收住（说话头连续说到约 150 秒以内内容是准确的；可用 `SOPHON_MAX_SPEECH_S` 调整）。实测约 2 分钟以内的回复都能完整说完。请求中途取消后，槽位立即释放。
- 多张卡：每张卡起一个实例（`GPU=1 PORT=8001 bash start.sh` …），前面放负载均衡。

## 其他显卡

在一张 RTX PRO 6000（Blackwell，96 GB）上实测：能安装、能运行，单路首包 0.42–0.47 秒，但一张卡只能跟上**约 4–8 路并发**
（8 路时有一两条回复落后 0.4–0.6 秒；12 路及以上全部落后）。发声的两段是由很多小的 PyTorch 计算核组成的，这张卡执行它们比
H100 慢约一倍。96 GB 的卡上显存占用约 76 GB。在这类显卡上需要更高并发时，请用 Tag 或 Flash。

在比 H100 系列更新的显卡上，请设置 `CUDA_HOME`（例如 `CUDA_HOME=/usr/local/cuda-13.0 bash start.sh`），让 vLLM 在首次启动时
为这张卡编译它的计算核。

## 接口说明

- `/v1/chat/completions`：系统提示词请用 `config/system_prompt.json` 里的那一段（模型是配着它调的，不带的话声音标签会少很多），
  然后把用户语音作为 `input_audio` 传入。设置 `"modalities": ["text","audio"]`，可选 `"language"`。文字增量里已去掉标签；
  语音增量是 base64 的 WAV 块（24 kHz）。见 `client_example.py`。
- `/v1/realtime`：OpenAI Realtime 风格的会话。持续发送 `input_audio_buffer.append`；在 `session.update` 里加上
  `"extra_body": {"auto_response": true, "language": "zh"}`。什么时候接话由模型自己判断。

## 设置（`start.sh`）

| 变量 | 默认值 | 含义 |
|---|---|---|
| `GPU`、`PORT` | `0`、`8000` | 显卡编号，HTTP / WebSocket 端口 |
| `MODEL_DIR` | `./model` | 模型目录 |
| `SLOTS` | `16` | 说话头同时说的回复数；更多的请求会等空位 |
| `MPS` | `1` | 用 CUDA MPS 让三段共用这张卡（强烈建议打开） |

## 目录内容

- `plugin/`：vLLM-Omni 插件（`sophon_realtime`）。三段：思考器（听、写、判断话轮）→ E2E 说话头（连续声音向量，边写边喂文字）
  → 解码器（2 步 DiT + 声码器）。第二、三段包的是 `../sophon_expressive` 里的引擎；vLLM-Omni 负责调度它们、在段之间传数据。
- `config/`：部署配置、系统提示词、VAD 模型。`start.sh` 会打开 CUDA MPS，让三段共用显卡。

许可：Apache-2.0。第三方组件见 [NOTICE](../NOTICE)。
