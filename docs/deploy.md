# Deploying Sophon-Realtime v1

[中文](deploy_CN.md)

Sophon-Realtime v1 runs as three local services:

| Service | What it does | Default port | GPU |
|---|---|---|---|
| Thinker | Listens to the user, decides when the user has finished, writes the reply (with sound tags). vLLM 0.29 + the reply LoRA. | 8300 | 1 × 80 GB |
| Speaking engine | Turns the reply into speech as it is being written: talker → vector frames → E2 → 24 kHz audio. | 8120 | 1 × 80 GB |
| Gateway | WebSocket API and the browser demo. Streams the microphone in, runs turn-taking, plays the reply, handles barge-in. | 8000 | – |

## Requirements

- Linux, NVIDIA driver 580 or newer (the wheels are built for CUDA 13), Python 3.10+.
- **Two 80 GB GPUs** (H100 / A100 80G / H800 …): one for the thinker, one for the speaking engine. A single-GPU build is in progress.
- About 80 GB of disk for the weights.

## Install

```bash
git clone https://github.com/adventists-ai/sophon-realtime
cd sophon-realtime
bash scripts/install.sh          # two virtual environments + model download (ModelScope)
```

- In mainland China, add a PyPI mirror: `PIP_INDEX_URL=https://mirrors.cloud.tencent.com/pypi/simple bash scripts/install.sh`.
- Already downloaded the model? `SKIP_DOWNLOAD=1 MODEL_DIR=/path/to/Sophon-Realtime-v1 bash scripts/install.sh`.
- The thinker must run on **vLLM 0.29**. vLLM 0.30 changes how often a half-finished sentence is judged as finished.

## Start

```bash
SOPHON_MODEL_DIR=$PWD/Sophon-Realtime-v1 THINKER_GPU=0 TALKER_GPU=1 bash scripts/start.sh
```

The first start takes 3–5 minutes (weights are loaded and the speaking engine captures its CUDA graphs). Then open `http://<server>:8000/` and talk. Use headphones so the model does not hear itself.

`bash scripts/stop.sh` stops everything. Logs are in `logs/`.

| Variable | Default | |
|---|---|---|
| `PORT` | 8000 | gateway / web demo |
| `THINKER_GPU`, `TALKER_GPU` | 0, 1 | GPU indices |
| `SOPHON_REPLY_LORA` | `$SOPHON_MODEL_DIR/adapters/tag` | reply LoRA, e.g. your own [fine-tuned](../finetune/README.md) one |
| `LORA_RANK` | 16 | max rank of the reply LoRA |
| `T32_SLOTS` | 8 | conversations the speaking engine keeps open at once |

## WebSocket API (`/ws`)

Streaming (full duplex), what the web demo uses:

1. `{"type": "config", "lang": "zh" | "en", "history": true}`
2. Send the microphone as binary frames: 16 kHz mono PCM16, any chunk size (the demo sends 512 samples).
3. Receive:
   - `{"type": "turn_commit", ...}`: the model decided you finished and is answering;
   - `{"type": "text", "delta": "..."}`: reply text, including sound tags such as `[laughter]` (they are performed, not spoken);
   - binary frames: reply audio, 24 kHz mono PCM16;
   - `{"type": "barge_in"}`: you started talking, stop playback;
   - `{"type": "metrics", ...}`, then `{"type": "done"}`.

One-shot (one user turn, for testing and benchmarks):

```json
{"type": "turn", "audio_b64": "<wav, any rate>", "lang": "zh"}
```

The reply comes back the same way (text, audio, metrics, done).

## Files in the model repository

| Path | |
|---|---|
| `base/` | shared 32B weights (thinker, and the trunk of the talker) |
| `adapters/tag/` | reply LoRA that writes sound tags (`[laughter]`, `[cough]`, `<strong>…</strong>` …) |
| `talker/` | talker LoRA and heads |
| `e2/` | E2 decoder and HiFT vocoder |
| `voices/` | default voice |

## Limits of this release

- One built-in voice; custom voices are not available yet.
- Two GPUs per deployment; concurrency is a few conversations at full quality.
- Replies are written in Chinese or English (the thinker understands more languages).
