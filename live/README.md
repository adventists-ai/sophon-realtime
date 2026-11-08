# Live mode: a drop-in for the OpenAI GPT-Live API

`sophon_live` is a gateway that speaks the **OpenAI GPT-Live protocol** (`/v1/live/sessions`, client delegation) and runs a Sophon-Realtime engine (Tag or Flash) behind it. Clients written for GPT-Live connect by changing only the URL and key.

Sophon keeps the voice: it listens, decides when it's its turn, and talks. When a request needs a lookup or an action (time, weather, memory, news, device control), it says a short line such as "Let me check that", hands a task to **your** backend through `session.delegation.created`, and speaks the result in its own words when your backend answers with `session.commentary.append`.

```
GPT-Live client ──GPT-Live protocol──▶ sophon_live.gateway ──▶ Tag / Flash engine (/v1/realtime + tool bridge)
                 ◀── delegation.created ──┘        ▲
your backend ─── commentary.append / thinking.append ┘
```

## Run

Start a Tag or Flash engine first (see [`../tag`](../tag/README.md) or [`../flash`](../flash/README.md)). The gateway talks to the engine's tool bridge, which listens on `SOPHON_BRIDGE_PORT` (127.0.0.1 only). Flash's `start.sh` sets it to `PORT + 700`; for Tag, set it yourself when you start the engine.

```bash
# engine on GPU 0, port 8000, tool bridge 8700
cd sophon-realtime/flash && GPU=0 PORT=8000 SOPHON_BRIDGE_PORT=8700 bash start.sh

# gateway (same Python environment as the engine; uses a small Qwen3-ASR-0.6B for the user transcript)
cd ../live
python -m sophon_live.gateway --port 8780 \
  --engine ws://127.0.0.1:8000/v1/realtime --bridge http://127.0.0.1:8700 \
  --asr /path/to/Qwen3-ASR-0.6B
```

Then point a GPT-Live client at `ws://HOST:8780/v1/live/sessions`. Open `http://HOST:8780/` for a browser test page (microphone, delegation cards, a demo backend and the protocol event log).

## Protocol coverage

- Client events: `session.start` (instructions, voice, `delegation: {type: client}`, `input` history), `session.input_audio.append`, `session.commentary.append` (spoken result), `session.thinking.append` (background context, not read out), `session.instructions.append`, `session.close`.
- Server events: `session.started`, `session.output_audio.delta` (continuous ~100 ms frames, silence when idle), `session.output_transcript.delta` (paced with playback), `session.input_transcript.delta`, `session.delegation.created` (adds an extra `task` field with what Sophon handed over), `session.commentary.appended`, `session.usage.updated`, `session.closed`, `error`.
- Barge-in is handled server-side: when the user talks over Sophon, playback stops.
- Optional settings: `SOPHON_LIVE_API_KEYS` (comma-separated bearer keys), `SOPHON_LIVE_ALLOW_ORIGINS` (browser origins allowed; other `Origin` headers are rejected, as in GPT-Live), `SOPHON_LIVE_VOICE`.

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
