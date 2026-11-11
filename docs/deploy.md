# Deploying the E2E build

[中文](deploy_CN.md)

The E2E build runs on **one 80 GB GPU**. Weights: [HF](https://huggingface.co/adventists-ai/Sophon-Realtime-32B-E2E) · [ModelScope](https://www.modelscope.cn/models/AdventistsAI/Sophon-Realtime-32B-E2E).

It runs as three local services on the same GPU:

| Service | What it does | Default port |
|---|---|---|
| Thinker | Listens to the user, decides when the user has finished, writes the reply (with sound tags). vLLM 0.29 + the reply LoRA. | 8300 |
| Speaking engine | Turns the reply into speech as it is being written: talker (about 350M parameters) → vector frames → decoder → 24 kHz audio. All conversations are batched in one loop. | 8120 |
| Gateway | WebSocket API and the browser demo. Streams the microphone in, runs turn-taking, plays the reply, handles barge-in. | 8000 |

## Requirements

- Linux, NVIDIA driver 580 or newer (the wheels are built for CUDA 13), Python 3.10+.
- **One 80 GB GPU** (H100 / A100 80G / H800 …). About 70 GB of GPU memory is used.
- CUDA MPS (`nvidia-cuda-mps-control`, shipped with the NVIDIA driver). `scripts/start.sh` starts its own MPS daemon for the GPU so the thinker and the speaking engine use it at the same time. Without MPS it still runs, but the two processes take turns on the GPU: first audio for one user goes from about 0.25 s to about 0.6 s and concurrency drops.
- About 75 GB of disk for the weights.

## Install

```bash
git clone https://github.com/adventists-ai/sophon-realtime
cd sophon-realtime
bash scripts/install.sh          # two virtual environments + model download (ModelScope)
```

- In mainland China, add a PyPI mirror: `PIP_INDEX_URL=https://mirrors.cloud.tencent.com/pypi/simple bash scripts/install.sh`.
- Already downloaded the model? `SKIP_DOWNLOAD=1 MODEL_DIR=/path/to/Sophon-Realtime-32B-E2E bash scripts/install.sh`.
- Upgrading from the two-GPU release (weights `v1.1.0` or earlier): download the weights again; the new ones have a `talker220/` folder and no longer need `talker/`.

## Start

```bash
SOPHON_MODEL_DIR=$PWD/Sophon-Realtime-32B-E2E GPU=0 bash scripts/start.sh
```

The first start takes about 5 minutes (weights are loaded and the speaking engine captures its CUDA graphs). Then open `http://<server>:8000/` and talk. Use headphones so the model does not hear itself.

`bash scripts/stop.sh` stops everything, including the MPS daemon it started. Logs are in `logs/`.

| Variable | Default | |
|---|---|---|
| `GPU` | 0 | GPU index |
| `PORT` | 8000 | gateway / web demo |
| `SLOTS` | 16 | conversations the speaking engine can speak for at the same time |
| `MPS` | 1 | 0 = do not use CUDA MPS |
| `THINKER_MEM` | 0.55 | share of GPU memory given to the thinker |
| `SOPHON_REPLY_LORA` | `$SOPHON_MODEL_DIR/adapters/tag` | reply LoRA, e.g. your own [fine-tuned](../finetune/README.md) one |
| `LORA_RANK` | 16 | max rank of the reply LoRA |
| `S220_NT` | 2 | decoder steps per audio chunk; 4 sounds slightly cleaner and costs about twice the decoder time |

## Performance (one H100 80 GB, measured from a fresh install)

Spoken questions in, spoken answers out, end to end (thinker + speaking engine + gateway on the same GPU). First audio is measured from the moment the request is sent to the first audio chunk received.

| Users arriving within 10 s | First audio, median / P90 | Replies whose playback fell more than 0.3 s behind |
|---|---|---|
| 1 | 0.25 s | 0 |
| 8 | 0.44 / 0.77 s | 0 of 8 |
| **16** | **0.44 / 0.56 s** | **0 of 16** |
| 24 | 0.58 / 0.94 s | 7 of 24 |
| 32 | 0.67 / 0.80 s | 23 of 32 |

Sustained load, 16 conversations that all start at the same moment and run five turns each (80 replies): first audio 0.51 s median / 0.62 s P90; 10 of the 80 replies fell more than 0.3 s behind at some point (worst 0.59 s). With 8 such conversations: 0.40 / 0.48 s, none behind.

**Recommended: up to 16 users per GPU.** More GPUs: one instance per GPU (`GPU=1 PORT=8001 …`) behind a load balancer.

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

## Sound tags

The talker performs these tags instead of reading them aloud. The thinker writes the ones in the first row on its own; the others are performed when they appear in the reply, for example from your own fine-tuned reply LoRA or in text you send to the speaking engine yourself (`/tts`).

| Tag | |
|---|---|
| `[laughter]` `[cough]` `[sigh]` `[breath]` | a sound at that point in the sentence |
| `[cry]` `[clear]` `[gasp]` | a sob, a throat clear, a sharp intake of breath (accepted, not benchmarked yet) |
| `<strong>word</strong>` | say the word with emphasis |
| `<laughter>some words</laughter>` | say the words while laughing |

## Files in the model repository

| Path | |
|---|---|
| `base/` | 32B weights of the thinker |
| `adapters/tag/` | reply LoRA that writes sound tags |
| `talker220/` | the talker: weights, text embedding table, tokenizer |
| `e2/` | decoder and HiFT vocoder |
| `voices/` | default voice |

## Limits of this release

- One built-in voice; voice cloning is not available in this build (use [Tag](../tag/README.md) or [Flash](../flash/README.md) for that).
- Replies are spoken in Chinese or English.
- One reply can be at most about 4.6 minutes of speech (and about 960 text tokens); a longer reply ends cleanly at that point and the other conversations are not affected.
- A sound at the very end of a sentence is held to about 1.6 s.
