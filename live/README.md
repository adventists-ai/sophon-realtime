# Live mode: a drop-in for the OpenAI GPT-Live API

`sophon_live` is a gateway that speaks the **OpenAI GPT-Live protocol** (`/v1/live/sessions`, client delegation) and runs a Sophon-Realtime engine (Tag or Flash) behind it. Clients written for GPT-Live connect by changing only the URL and key.

Sophon keeps the voice: it listens, decides when it's its turn, and talks. When a request needs a lookup or an action (time, weather, memory, news, device control), it says a short line such as "Let me check that", hands a task to **your** backend through `session.delegation.created`, and speaks the result in its own words when your backend answers with `session.commentary.append`.

```
GPT-Live client ──GPT-Live protocol──▶ sophon_live.gateway ──▶ Tag / Flash engine (/v1/realtime + tool bridge)
                 ◀── delegation.created ──┘        ▲
your backend ─── commentary.append / thinking.append ┘
```

## Run

Live mode is not a separate install: it is a small gateway that runs next to a Tag or Flash engine started with the one-command scripts, in the same Python environment. The engine's `start.sh` already opens the tool bridge the gateway needs (on `PORT + 700`, 127.0.0.1 only).

```bash
# 1. start the engine as usual (Tag here; Flash works the same way)
cd sophon-realtime/tag && GPU=0 PORT=8000 bash start.sh

# 2. start Live mode next to it
cd ../live && BUILD=tag PORT=8000 LIVE_PORT=8780 bash start_live.sh
```

GPT-Live clients connect to `ws://HOST:8780/v1/live/sessions`; `http://HOST:8780/` is a browser test page (microphone, delegation cards, a demo backend and the protocol event log). Stop with `LIVE_PORT=8780 bash stop_live.sh`.

The gateway loads a small ASR model for the user transcript (`Qwen/Qwen3-ASR-0.6B-hf`, about 2 GB of GPU memory). In mainland China, download it from ModelScope first: `modelscope download --model Qwen/Qwen3-ASR-0.6B-hf --local_dir ./asr`, then `SOPHON_LIVE_ASR=./asr bash start_live.sh`.

## Protocol coverage

- Client events: `session.start` (instructions, voice, `delegation: {type: client}`, `input` history), `session.input_audio.append`, `session.commentary.append` (spoken result), `session.thinking.append` (background context, not read out), `session.instructions.append`, `session.close`.
- Server events: `session.started`, `session.output_audio.delta` (continuous ~100 ms frames, silence when idle), `session.output_transcript.delta` (paced with playback), `session.input_transcript.delta`, `session.delegation.created` (adds an extra `task` field with what Sophon handed over), `session.commentary.appended`, `session.usage.updated`, `session.closed`, `error`.
- Barge-in is handled server-side: when the user talks over Sophon, playback stops.
- Optional settings: `SOPHON_LIVE_API_KEYS` (comma-separated bearer keys), `SOPHON_LIVE_ALLOW_ORIGINS` (browser origins allowed; other `Origin` headers are rejected, as in GPT-Live), `SOPHON_LIVE_VOICE`.

## OpenAI Realtime face: LiveKit and Pipecat

The same gateway also serves an **OpenAI Realtime** compatible endpoint at `ws://HOST:8780/v1/realtime` (GA event names, function calling, barge-in truncation, PCM16 and G.711). Voice-agent frameworks that support OpenAI Realtime work by changing the base URL, no new plugin needed:

| Framework | What to change | Example | Tested |
|---|---|---|---|
| LiveKit Agents | `openai.realtime.RealtimeModel(base_url="http://HOST:8780/v1", ...)` | [examples/livekit_agent.py](examples/livekit_agent.py) | livekit-agents 1.8.11: first audio about 0.6 s after the user stops |
| Pipecat | `OpenAIRealtimeLLMService(base_url="ws://HOST:8780/v1/realtime", ...)` | [examples/pipecat_bot.py](examples/pipecat_bot.py) | pipecat-ai 1.15.0: first audio about 0.3 s after the user stops |

Set `SOPHON_LIVE_REALTIME_KEYS_FILE` (one key per line) to require a bearer key on `/v1/realtime`.

## Front + back office (optional)

Set `SOPHON_LIVE_BACKEND=<model>` with an OpenAI-compatible endpoint (`SOPHON_LIVE_BACKEND_URL`, `SOPHON_LIVE_BACKEND_KEY`) and the gateway answers delegations itself with a larger model: Sophon stays on the line, the back office reasons and calls tools. With DeepSeek V4 Pro as the back office, Big Bench Audio rises from 81.2 to about 83.

## Test

`python live_test.py --url ws://127.0.0.1:8780/v1/live/sessions` plays the 14 recorded questions in `cases/` (7 that should be delegated, 7 that should not) with a mock backend and prints whether each one was delegated, the transcript and the time to first audio.

Measured on one H100 (mock backend, 14 recorded questions):

| Engine | Lookups delegated and answered | Answered directly when it should | First audio, direct / delegated |
|---|---|---|---|
| Tag | 7 / 7 | 6 / 7 ("tell me a joke" was delegated) | about 0.4–0.6 s / 0.6–0.8 s |
| Flash | 7 / 7 | 5 / 7 ("tell me a joke" and "why is the sky blue?" were delegated) | about 0.33 s / 0.7 s |

## Limits

- Sometimes delegates a question it could answer itself, or says a filler line without delegating.
- The first session right after the engine starts may not respond; run one warm-up session (`client_example.py` does this).
- Sound tags appear in the output transcript (for example `[laughter]`), the way GPT-Live shows acoustic events.
