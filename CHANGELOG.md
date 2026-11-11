# Changelog

## 2026-11-11 (hardening): sophon-realtime 1.0.4

- Tag build, a hard guard that does not depend on segmenting: the flow decoder now only sees the last part of a long request (at most 2,800 mel frames with the prompt, `SOPHON_FLOW_MAX_FRAMES`; at least 50 tokens of context before the new audio, `SOPHON_FLOW_CTX_TOKENS`). If a flow call still fails, only that request loses that audio chunk; the stage and the other sessions keep running.
- Tested on one H100 with segmenting and the HTTP speech cap both switched off, so every reply ran into the old limit: 16 concurrent realtime sessions with 4,096-token replies plus 4 concurrent long HTTP requests ran with no TensorRT errors, and a fresh session afterwards answered normally. With the default settings: 32 concurrent long sessions with half of them dropping their connection abruptly mid-reply, replies without any punctuation, and Chinese and English replies over 3 minutes all ran without errors.

## 2026-11-11 (latest): Flash voice cloning

- Flash: zero-shot voice cloning ([#2](https://github.com/adventists-ai/sophon-realtime/issues/2)). Put a 3-10 s clip at `model/voices/<name>.wav` and use `"voice": "<name>"` in `/v1/chat/completions` or `/v1/realtime`; no fine-tuning or restart. Voices are re-read when the file changes, and an unknown or unreadable voice falls back to `chelsie` with a warning instead of failing the request. See [flash/README.md](flash/README.md#zero-shot-voice-cloning). Flash plugin 0.2.0.

## 2026-11-11 (later): long replies

- Fix: on the Tag build, a very long spoken reply (over about 60 s of audio, e.g. a session with a large `max_response_output_tokens`) could crash the TensorRT flow stage and end every open session ([HF discussion #1](https://huggingface.co/adventists-ai/Sophon-Realtime-32B-Tag/discussions/1), thanks to Trelis Research). The streaming flow decoder re-runs over the whole reply, so a long reply went past the TensorRT engine's 3000-frame profile.
- Realtime sessions now speak long replies in segments: the model writes about 120 tokens at a time, each segment ends at a sentence end, and the next one starts at once while the previous is still playing, with no gap. Each segment is short enough for the engine, so a reply has no length limit other than the session's token budget. Segment size: `SOPHON_SEG_TOKENS` (0 turns segmenting off).
- Requests that are not segmented (HTTP `/v1/chat/completions` with a large `max_tokens`) now end their speech at a sentence end before 50 s (`SOPHON_MAX_SPEECH_S`); the text reply is not cut.
- If the flow engine still fails on a batch, it now retries the requests one at a time instead of stopping the stage.
- Idle realtime sessions are kept for 300 s instead of 60 s (`idle_ttl_s`).
- Tested with Trelis Research's protocol: 16 concurrent `/v1/realtime` sessions, 80 ms float32 16 kHz frames in real time, a spoken prompt and then 163.84 s of silence, 4 batches plus a fresh session, from a fresh restart: 65 of 65 sessions completed, replies up to 288 s of audio, longest segment 41 s, no errors. First-audio latency for short replies is unchanged (about 0.35 s alone, 1.1-1.5 s at 8 and 2.1-2.4 s at 16 concurrent sessions on one H100).
- `sophon-realtime` 1.0.3 on PyPI with these changes (`pip install -U sophon-realtime`). Flash replies already reach about 160 s without this problem; the E2E build has not been tested for very long replies.

## 2026-11-11

- Fix: on the Tag build, the first realtime (`/v1/realtime`) session after a cold start could end with no reply, while HTTP inference worked ([HF discussion #1](https://huggingface.co/adventists-ai/Sophon-Realtime-32B-Tag/discussions/1), thanks to Trelis Research). A reply append that the framework did not accept in time was dropped for good. It is now rolled back and sent again; a speculative draft that never reached the engine is no longer treated as released; the unconfirmed-append timeout is 15 s instead of 2 s (`SOPHON_RES_TIMEOUT`).
- The server now warms itself up once it is ready: three turn questions plus one short throwaway realtime session (about 20 s), so the first real session is as fast as later ones. Set `SOPHON_WARMUP=0` to skip.
- `sophon-realtime` 1.0.2 on PyPI with these fixes (`pip install -U sophon-realtime`). The Flash plugin (`flash/plugin`) has the same fix and warm-up, tested the same way on a Flash instance.

## 2026-11-09

- `sophon-realtime` 1.0.1 on PyPI: `sophon-realtime serve` now serves the model under the name `adventists-ai/Sophon-Realtime-32B-Tag` (alias `sophon-realtime`).
- Live mode: LiveKit Agents and Pipecat examples for the OpenAI Realtime compatible endpoint (`live/examples/`), tested with livekit-agents 1.8.11 and Pipecat v1.15.0.

## 2026-11-08: v1.0

- First public release of the Sophon-Realtime v1 family: Sophon-Realtime-32B-Tag, Sophon-Realtime-32B-Flash and Sophon-Realtime-32B-E2E (research preview).
- One-command install and start scripts for Tag and Flash (vLLM-Omni, one 80 GB GPU), `pip install sophon-realtime`.
- Live mode: GPT-Live and OpenAI Realtime compatible gateway (`live/`).
