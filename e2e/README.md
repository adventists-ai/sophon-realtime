# Sophon-Realtime E2E build on vLLM-Omni — one GPU, one command

[中文](README_CN.md)

The E2E build of Sophon-Realtime, served as **one vLLM-Omni model** on a single 80 GB GPU, with the same commands, APIs and
client as the [Tag](../tag/README.md) and [Flash](../flash/README.md) builds. It listens to your speech, writes a reply that
may contain sound tags (`[laughter]`, `[cough]`, `[sigh]`, `[breath]`, `<strong>…</strong>`, `<laughter>…</laughter>`), and
speaks it while it is still writing. Tags are performed, never read aloud, and are removed from the text stream.

This is the second way to run E2E. The first one, our own engine ([docs/deploy.md](../docs/deploy.md)), is a little faster
(see the table below). Both use the same talker and decoder weights and produce the same voice.

| | |
|---|---|
| Weights | [ModelScope](https://www.modelscope.cn/models/AdventistsAI/Sophon-Realtime-32B-E2E) · [Hugging Face](https://huggingface.co/adventists-ai/Sophon-Realtime-32B-E2E) (`thinker/`, `talker220/`, `e2/`, `voices/`, `config.json`) |
| GPU | one 80 GB GPU of the H100 class, about 67 GB per instance. See [Other GPUs](#other-gpus) |
| APIs | `ws://HOST:PORT/v1/realtime` (full duplex: turn-taking, barge-in) · `POST /v1/chat/completions` (audio in → text + audio stream) |

## Quick start

```bash
git clone https://github.com/adventists-ai/sophon-realtime && cd sophon-realtime/e2e
bash install.sh                 # Python 3.12 venv, vLLM 0.30, vLLM-Omni 0.30, plugin, torch 2.14.1, then downloads the weights to ./model (~41 GB)
GPU=0 PORT=8000 bash start.sh   # about 5 min on H100 (the first start compiles kernels and takes a few minutes longer); warms up before it says READY
python client_example.py --wav my_question.wav --lang en
bash stop.sh
```

- Mirror in mainland China: `PIP_INDEX=https://mirrors.aliyun.com/pypi/simple bash install.sh`.
- Weights already downloaded: `SKIP_DOWNLOAD=1 bash install.sh`, then `MODEL_DIR=/path/to/Sophon-Realtime-32B-E2E bash start.sh`.
  The model directory needs `thinker/`, `talker220/`, `e2/`, `voices/` and `config.json`; `base/` and `adapters/` are only for the own engine.
- Keep the whole repository: the plugin uses the engine code in `../sophon_expressive`.
- `install.sh` installs torch 2.14.1 after vLLM on purpose. With an older torch the voice stages need about 50 GB more GPU memory.
  The start-up log then shows one warning that `vllm.third_party.deep_gemm` failed to import; that module is not used by this model.
- One built-in voice (`chelsie`), Chinese and English; any other voice by zero-shot cloning (below).

## Zero-shot voice cloning (new in 1.3.0)

Give the server a short clip of the voice you want and use its name like the built-in voice. No fine-tuning, no restart.

```bash
cp alice.wav model/voices/alice.wav   # 5-12 s of clean speech from one speaker (wav or flac, 16 kHz or more)
python client_example.py --wav my_question.wav --lang en --voice alice
```

- The decoder takes the clip as its reference prompt (its speech tokens, mel frames and speaker embedding, computed as for Tag's voice
  files). It needs two small models from the Tag release, `speech_tokenizer_v3.onnx` and `campplus.onnx` (about 1 GB); `install.sh`
  downloads them to `model/clone_frontend/talker/` (`SKIP_CLONE=1` skips this; `SOPHON_CLONE_FRONTEND=/path/to/Tag/model/talker` uses a
  copy you already have). Voices can also live outside the model directory: `SOPHON_VOICES=/path/to/voices`.
- The voice is prepared the first time it is used and then cached; first audio is as fast as with the built-in voice. To replace a voice,
  overwrite the file; to remove it, delete the file. Voice names are lower case (`a-z 0-9 _ - .`). A clip shorter than about 5 s, or one
  that cannot be read, falls back to the built-in voice (the log says why).
- Works with `/v1/chat/completions` (`"voice": "alice"`) and `/v1/realtime` (`session.update` → `"voice": "alice"`), in every language
  the model speaks; a voice cloned from one language can speak another.
- **Only clone your own voice or a voice you have permission to use. Do not use it to impersonate or deceive anyone.**

## Performance (one H100 80 GB, measured)

Spoken question in, spoken answer out, `/v1/chat/completions`, users arriving within 10 s.

| Concurrent users | First audio, median / P90 | Replies that fall more than 0.3 s behind playback | Own engine, for comparison |
|---|---|---|---|
| 1 | about 0.35 s | 0 | 0.25 s |
| 8 | 0.40–0.45 / 0.84–0.95 s | 0 of 8 | 0.44 / 0.77 s, 0 of 8 |
| **16** | **0.58–0.65 / 0.71–0.87 s** | 0–2 of 16 (by at most 0.4 s) | 0.44 / 0.56 s, 0 of 16 |
| 24 | 0.79–0.88 / 1.7–2.8 s | 1–3 of 24 | 0.58 / 0.94 s, 7 of 24 |
| 16 users × 5 turns each | 0.64 / 0.84–0.91 s | 0–1 of 80 | 0.51 / 0.62 s, 10 of 80 |

- **Recommended: up to 16 concurrent users per GPU.**
- Full duplex (`/v1/realtime`): about 0.45 s (median) from the end of your speech to the first voice.
- Non-verbal sounds: the talker output is bit-identical to the own engine's, so its NVV-SuperBench result applies (0.75 English / 0.85 Chinese).
- Long replies are spoken to their end, however long (tested up to 14 minutes): the talker speaks them in segments of about 25–40 s, each a fresh context on the rest of the text, so it stays accurate. Requests that are cancelled free their slot at once.
- More GPUs: one instance per GPU (`GPU=1 PORT=8001 bash start.sh`, …) behind a load balancer.

## Other GPUs

Measured on one RTX PRO 6000 (Blackwell, 96 GB): it installs and runs, one user gets first audio in 0.42–0.47 s, but one GPU
keeps up with only **about 4–8 concurrent users** (at 8, one or two replies fall 0.4–0.6 s behind; at 12 and more, all do).
The voice stages run as many small PyTorch kernels, which this card executes about 2× slower than an H100. Memory use is
about 76 GB on a 96 GB card. If you need more users per GPU on such cards, use Tag or Flash.

On GPUs newer than the H100 family, set `CUDA_HOME` (for example `CUDA_HOME=/usr/local/cuda-13.0 bash start.sh`) so that
vLLM can compile its kernels for the card at the first start.

## API notes

- `/v1/chat/completions`: use the system prompt in `config/system_prompt.json` (the model was tuned with it; without it it
  uses far fewer sound tags), then the user audio as `input_audio`. Set `"modalities": ["text","audio"]`, optionally
  `"language"`. Text deltas have tags removed; audio deltas are base64 WAV chunks (24 kHz). See `client_example.py`.
- `/v1/realtime`: OpenAI-Realtime-style session. Send `input_audio_buffer.append` continuously; put
  `"extra_body": {"auto_response": true, "language": "en"}` in `session.update`. The model decides turn-taking itself.

## Settings (`start.sh`)

| Variable | Default | Meaning |
|---|---|---|
| `GPU`, `PORT` | `0`, `8000` | GPU index and HTTP / WebSocket port |
| `MODEL_DIR` | `./model` | model directory |
| `SLOTS` | `16` | replies the talker speaks at the same time; more requests wait for a free slot |
| `MPS` | `1` | share the GPU between the three stages through CUDA MPS (strongly recommended) |

## What's inside

- `plugin/`: the vLLM-Omni plugin (`sophon_realtime`). Three stages: thinker (listens, writes, decides turns) → E2E talker
  (continuous voice vectors, fed text while it is being written) → decoder (2-step DiT + vocoder). The second and third stage
  wrap the engine in `../sophon_expressive`; vLLM-Omni schedules them and moves the data between them.
- `config/`: deploy config, system prompt, VAD model. `start.sh` turns on CUDA MPS so the three stages share the GPU.

License: Apache-2.0. Third-party components: [NOTICE](../NOTICE).
