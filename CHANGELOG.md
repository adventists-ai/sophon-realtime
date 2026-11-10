# Changelog

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
