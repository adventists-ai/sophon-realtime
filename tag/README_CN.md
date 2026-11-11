# Sophon-Realtime Tag 版：单卡、一条命令（vLLM-Omni）

[English](README.md)

Tag 版整体作为**一个** vLLM-Omni 模型跑在一张 80 GB 显卡上：听用户说话 → 写回复（可带声音标签 `[laughter]` `[breath]`
`[sigh]` `[cough]` `<strong>…</strong>` `<laughter>…</laughter>`）→ 边写边说。标签会被“演”出来，不会被念出来，文字流里也会去掉。

| | |
|---|---|
| 权重 | [魔搭](https://www.modelscope.cn/models/AdventistsAI/Sophon-Realtime-32B-Tag) · [Hugging Face](https://huggingface.co/adventists-ai/Sophon-Realtime-32B-Tag) |
| 显卡 | 一张 80 GB（H100 / H800 / A100 80G），每个实例约 65 GB |
| 接口 | `ws://HOST:PORT/v1/realtime`（全双工：话轮、打断、附和）· `POST /v1/chat/completions`（语音进 → 文字 + 语音流） |

## 快速上手

```bash
git clone https://github.com/adventists-ai/sophon-realtime && cd sophon-realtime/tag
bash install.sh                 # Python 3.12 虚拟环境、vLLM 0.30、vLLM-Omni 0.30、插件，并把权重下载到 ./model（约 42 GB）
GPU=0 PORT=8000 bash start.sh   # 首次启动 15–20 分钟（编译内核、建 TensorRT 引擎），之后 5–8 分钟；预热完才显示 READY
python client_example.py --wav 我的问题.wav --lang zh --voice vivian_zh
bash stop.sh
```

- 国内镜像：`PIP_INDEX=https://pypi.tuna.tsinghua.edu.cn/simple bash install.sh`。
- 已经下好权重：`SKIP_DOWNLOAD=1 bash install.sh`，启动时 `MODEL_DIR=/权重目录 bash start.sh`。
- 音色：`chelsie`（默认，按语言自动选 `chelsie_zh` / `chelsie_en`）、`vivian_zh`、`ryan_en`、`brand_zh`、`brand_en`。

## 零样本音色克隆

给一段任意声音的录音，就能让智子用这个声音和你对话。不用微调，不用重启。

```bash
cp alice.wav model/voices/alice.wav     # 同一个人 3–10 秒的干净语音（wav 或 flac，采样率不限）
python client_example.py --wav 我的问题.wav --lang zh --voice alice
```

- 在 `/v1/chat/completions` 或 `/v1/realtime` 的 `session.update` 里写 `"voice": "alice"` 即可；参考音的语言可以和回复不同。
- 新放进去的录音，服务会在几秒内于后台准备好（每 5 秒扫描一次 voices 文件夹；`SOPHON_VOICE_SCAN=0` 关闭），首包和内置音色一样快。
  换音色直接覆盖文件，删音色直接删文件。音色名用小写（`a-z 0-9 _ - .`）；同名 `.pt` 优先于录音。声音标签对克隆音色同样有效。
- 找不到或读不了的音色会回落到 `chelsie`，服务日志里有警告，不会让会话失败。
- 需要 1.1.0 的说话模型（`talker/flow.pt` 及 ONNX，2026-11-11 已在 HF / 魔搭更新）：旧权重也能用，但新权重对没见过的声音还原得更像。
  `SOPHON_VOICES=/路径` 可把音色放在 `model/` 以外。
- **只克隆你本人或已获授权的声音，不得用于冒充他人或欺诈。**

## 性能（单张 H100 80 GB 实测）

| 并发（10 秒内陆续到达） | 首包 中位 / 最慢 | 卡顿（中位） |
|---|---|---|
| 1 路 | 0.67 秒 | 约 0 |
| 8 路 | 0.61 / 0.76 秒 | 0 |
| **16 路** | **0.75 / 1.07 秒** | 0.06 秒 |
| 24 路 | 1.36 / 2.11 秒 | 0.39 秒（开始排队） |

- 全双工（`/v1/realtime`）：用户说完到听到声音约 0.7 秒。
- **以上数字需要 TensorRT。** `install.sh` 会自动安装。没有 TensorRT 时说话段走纯 PyTorch，高并发下慢约 3 倍（16 路：首包约 2.4 秒、
  卡顿 1–1.5 秒）。可在服务日志里确认有 `Loaded flow-estimator TensorRT engine` 这一行。
- **建议每张卡最多 16 路并发。**
- 多卡：每张卡起一个实例（`GPU=1 PORT=8001 bash start.sh` ……），前面加负载均衡；每个 WebSocket 会话固定在一个实例上，容量基本按卡数线性增长。CPU 不是瓶颈（16 路时每个实例约 1.5 核）。

## 接口说明

- `/v1/chat/completions`：系统提示请用 `config/system_prompt.json` 里的（模型按它调过，不带会少写标签）；用户语音放 `input_audio`；`"modalities": ["text","audio"]`，可选 `"voice"`、`"language"`。文字流已去掉标签；音频流为 base64 WAV 块（24 kHz）。示例见 `client_example.py`。
- `/v1/realtime`：OpenAI Realtime 风格会话；持续发送 `input_audio_buffer.append`，`session.update` 里带 `"extra_body": {"auto_response": true, "language": "zh"}`。话轮由模型自己判断。

## 组成

- `plugin/`：vLLM-Omni 插件（`sophon_realtime`）。三段：思考器（听、写、判话轮）→ tag-tts 说话段（边收字边出语音 token）→ flow + HiFT 声码器（TensorRT，多路合批）。
- `config/`：部署配置、系统提示、VAD 模型。`start.sh` 默认开 CUDA MPS，让三段同时用卡。

许可：Apache-2.0。
