# Sophon-Realtime-32B-Flash：单卡、一条命令（vLLM-Omni）

全双工语音模型，整体作为**一个** vLLM-Omni 模型部署：听用户说话 → 写回复（可带声音标签 `[laughter]` `[cough]` `[sigh]` `[breath]`
`<laughter>…</laughter>` `<strong>…</strong>`）→ 边写边说。说话段每 80 毫秒出一帧声音，标签会被“演”出来，不会被念出来。

Flash 和 Tag 版共用同一个会写标签的思考器，区别在说话段：Flash 的说话段是自回归、每步一次前向的轻量结构，**首包更快、并发更高**；
Tag 版的笑更到位。两者接口相同。

## 性能（单张 H100 80 GB，FP8 思考器，`/v1/chat/completions`，用户语音 → 首个声音块）

| 负载 | 首包 中位 / P90 | 卡顿（中位） |
|---|---|---|
| 1 路 | **0.31 / 0.34 秒** | 0 |
| 20 路（10 秒内陆续到达） | 0.45 / 0.52 秒 | 0.09 秒 |
| 40 路（10 秒内） | 0.58 / 0.67 秒 | 0.37 秒 |
| 64 路（8 秒内） | 0.84 / 1.03 秒 | 1.9 秒（开始排队） |

- **建议每张 80 GB 卡最多约 40 路并发。** 多卡：每张卡起一个实例，前面加负载均衡。
- 显存：每个实例约 55 GB。首次启动要编译内核（约 10 分钟），之后 5–8 分钟。

### 声音标签（留出集，Chelsie 音色，DuplexJev 判定）

| 标签 | 中文 | 英文 |
|---|---|---|
| `[laughter]` 笑一声 | 83% | 77% |
| `<laughter>…</laughter>` 边笑边说 | 78% | 71% |
| `[cough]` 咳嗽 | 90% | 50%（8 句） |
| `[sigh]` 叹气（AST） | 90% | 100% |
| 平均字错率 | 0.9% | 1.0% |

- 标签从不被念出来；不写标签时基本不会乱笑。
- `<strong>` 重读这一版还很弱，下一版补。

## 快速上手

```bash
bash install.sh                 # 只需一次：Python 3.12 虚拟环境、vLLM 0.30、vLLM-Omni 0.30、插件（国内镜像：PIP_INDEX=https://pypi.tuna.tsinghua.edu.cn/simple）
# 把权重下载到 ./model（魔搭：modelscope download --model AdventistsAI/Sophon-Realtime-32B-Flash --local_dir ./model）
GPU=0 PORT=8000 bash start.sh
python client_example.py --wav 我的问题.wav --lang zh --voice chelsie
bash stop.sh
```

音色：`chelsie`（默认）、`brand`；语言用 `language` 指定（`zh` / `en`）。

## 接口说明
- `/v1/chat/completions`：系统提示请用 `config/system_prompt.json` 里的（模型按它调过，不带会少写标签）；用户语音放 `input_audio`；
  `"modalities": ["text","audio"]`，可选 `"voice"`、`"language"`。文字流保留标签（显示时可自行去掉）；音频流为 base64 WAV 块（24 kHz）。
- `/v1/realtime`：OpenAI Realtime 风格会话；持续发送 `input_audio_buffer.append`，话轮由模型自己判断。

## 目录
`model/`（思考器、说话段、音色）· `plugin/`（vLLM-Omni 插件 `sophon_realtime`）· `config/`（部署配置、系统提示、VAD）· `examples/`

许可：代码 Apache-2.0；模型权重 Apache-2.0，来源见 `NOTICE`。
