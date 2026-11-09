# Live 模式：OpenAI GPT-Live 接口的平替

`sophon_live` 是一个网关：对外完全按 **OpenAI GPT-Live 协议**（`/v1/live/sessions`，client delegation），后面接 Sophon-Realtime 引擎（Tag 或 Flash）。按 GPT-Live 写的客户端，只要改地址和 key 就能接入。

智子负责听和说：判断什么时候轮到自己、怎么接话。遇到要查询或办事的请求（时间、天气、记忆、新闻、设备控制），它先说一句「我帮你查一下」，通过 `session.delegation.created` 把任务交给**你的**后端；后端用 `session.commentary.append` 回结果后，它再用自己的话说出来。

## 运行

Live 模式不用单独安装：它是一个小网关，和用一键脚本启动的 Tag 或 Flash 引擎跑在一起，用同一个 Python 环境。引擎的 `start.sh` 已经打开了网关需要的工具桥（端口 `PORT + 700`，只监听 127.0.0.1）。

```bash
# 1. 照常启动引擎（以 Tag 为例，Flash 一样）
cd sophon-realtime/tag && GPU=0 PORT=8000 bash start.sh

# 2. 在旁边启动 Live 模式
cd ../live && BUILD=tag PORT=8000 LIVE_PORT=8780 bash start_live.sh
```

GPT-Live 客户端连 `ws://HOST:8780/v1/live/sessions` 即可；浏览器打开 `http://HOST:8780/` 是测试页（麦克风对话、委派卡片、演示后端、协议事件日志）。停止：`LIVE_PORT=8780 bash stop_live.sh`。

网关会加载一个小的语音识别模型做用户转写（`Qwen/Qwen3-ASR-0.6B-hf`，约 2 GB 显存）。国内建议先从魔搭下载：`modelscope download --model Qwen/Qwen3-ASR-0.6B-hf --local_dir ./asr`，再 `SOPHON_LIVE_ASR=./asr bash start_live.sh`。

## 前台 + 后台（可选）

设置 `SOPHON_LIVE_BACKEND=<模型名>` 和 OpenAI 兼容端点（`SOPHON_LIVE_BACKEND_URL`、`SOPHON_LIVE_BACKEND_KEY`），网关会用一个更大的模型自己处理委派：智子在前台说话，后台负责推理和调用工具。后台用 DeepSeek V4 Pro 时，Big Bench Audio 从 81.2 提到约 83。

## OpenAI Realtime 接口：LiveKit 和 Pipecat

同一个网关还提供 **OpenAI Realtime** 兼容接口 `ws://HOST:8780/v1/realtime`（GA 事件名、函数调用、打断截断、PCM16 和 G.711）。支持 OpenAI Realtime 的语音智能体框架，改一下地址就能用，不需要新插件：

| 框架 | 要改的地方 | 示例 | 实测 |
|---|---|---|---|
| LiveKit Agents | `openai.realtime.RealtimeModel(base_url="http://HOST:8780/v1", ...)` | [examples/livekit_agent.py](examples/livekit_agent.py) | livekit-agents 1.8.11：用户说完约 0.6 秒出声 |
| Pipecat | `OpenAIRealtimeLLMService(base_url="ws://HOST:8780/v1/realtime", ...)` | [examples/pipecat_bot.py](examples/pipecat_bot.py) | pipecat-ai 1.15.0：用户说完约 0.3 秒出声 |

需要鉴权时设置 `SOPHON_LIVE_REALTIME_KEYS_FILE`（每行一个 key），`/v1/realtime` 就会要求 bearer key。

## 实测（单张 H100，模拟后端，14 条录音）

| 引擎 | 该委派的：委派并转述结果 | 不该委派的：直接回答 | 首包（直接答 / 委派） |
|---|---|---|---|
| Tag | 7 / 7 | 6 / 7（「讲个笑话」被委派） | 约 0.4–0.6 秒 / 0.6–0.8 秒 |
| Flash | 7 / 7 | 5 / 7（「讲个笑话」和 "Why is the sky blue?" 被委派） | 约 0.33 秒 / 0.7 秒 |

测试脚本：`python live_test.py --url ws://127.0.0.1:8780/v1/live/sessions`。

## 已知局限

- 偶尔把自己能答的问题也委派出去，或者只说了过渡语却没有委派。
- 引擎刚启动后的第一个会话可能没有回应，先跑一次预热（`client_example.py` 会做）。
- 输出转写里会带声音标签（如 `[laughter]`），和 GPT-Live 显示声学事件的方式一致。
