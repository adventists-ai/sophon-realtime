# Sophon-Realtime Tag build — one GPU, one command (vLLM-Omni)

[中文](README_CN.md)

The Tag build of Sophon-Realtime runs as **one vLLM-Omni model** on a single 80 GB GPU. It listens to your speech, writes a
reply that may contain sound tags (`[laughter]`, `[breath]`, `[sigh]`, `[cough]`, `<strong>…</strong>`,
`<laughter>…</laughter>`), and speaks it while it is still writing. Tags are performed, never read aloud, and are removed
from the text stream.

| | |
|---|---|
| Weights | [ModelScope](https://www.modelscope.cn/models/AdventistsAI/Sophon-Realtime-32B-Tag) · [Hugging Face](https://huggingface.co/adventists-ai/Sophon-Realtime-32B-Tag) |
| GPU | one 80 GB GPU (H100 / H800 / A100 80G), ~65 GB per instance |
| APIs | `ws://HOST:PORT/v1/realtime` (full duplex: turn-taking, barge-in, backchannel) · `POST /v1/chat/completions` (audio in → text + audio stream) |

## Quick start

```bash
git clone https://github.com/adventists-ai/sophon-realtime && cd sophon-realtime/tag
bash install.sh                 # Python 3.12 venv, vLLM 0.30, vLLM-Omni 0.30, plugin, then downloads the weights to ./model (~42 GB)
GPU=0 PORT=8000 bash start.sh   # first start 15–20 min (kernels + TensorRT engines), later 5–8 min; warms up before it says READY
python client_example.py --wav my_question.wav --lang en --voice ryan_en
bash stop.sh
```

- Mirror in mainland China: `PIP_INDEX=https://pypi.tuna.tsinghua.edu.cn/simple bash install.sh`.
- Weights already downloaded: `SKIP_DOWNLOAD=1 bash install.sh`, then `MODEL_DIR=/path/to/Sophon-Realtime-32B-Tag bash start.sh`.
- Voices: `chelsie` (default; `chelsie_zh` / `chelsie_en` picked by language), `vivian_zh`, `ryan_en`, `brand_zh`, `brand_en`.

## Zero-shot voice cloning

Give it a short clip of any voice and talk to Sophon in that voice. No fine-tuning, no restart.

```bash
cp alice.wav model/voices/alice.wav     # 3–10 s of clean speech from one speaker (wav or flac, any sample rate)
python client_example.py --wav my_question.wav --lang en --voice alice
```

- Use `"voice": "alice"` in `/v1/chat/completions` or in `session.update` on `/v1/realtime`. The clip can be in another language than the reply.
- The server prepares new clips in the background within a few seconds (it scans the voices folder every 5 s; `SOPHON_VOICE_SCAN=0` turns
  this off), so first audio is as fast as with a built-in voice. Overwrite a file to replace a voice, delete it to remove it. Voice names are
  lower case (`a-z 0-9 _ - .`); a `.pt` of the same name takes precedence over the clip. Sound tags work with cloned voices too.
- An unknown or unreadable voice falls back to `chelsie` with a warning in the server log; it never fails the session.
- Needs the v1.3.1 voice model (`talker/flow.pt` + ONNX, updated on HF / ModelScope on 2026-11-11): older weights still work, but unseen
  voices sound much closer to the reference with the new ones. `SOPHON_VOICES=/path` keeps voices outside `model/`.
- **Only clone your own voice or a voice you have permission to use. Do not use it to impersonate or deceive anyone.**

## Performance (one H100 80 GB, measured)

| Concurrent users (arriving within 10 s) | First audio, median / max | Stutter (median) |
|---|---|---|
| 1 | 0.67 s | ~0 |
| 8 | 0.61 / 0.76 s | 0 |
| **16** | **0.75 / 1.07 s** | 0.06 s |
| 24 | 1.36 / 2.11 s | 0.39 s (queueing starts) |

- Full duplex (`/v1/realtime`): about 0.7 s from the end of your speech to the first voice.
- **These numbers need TensorRT.** `install.sh` installs it. Without it the voice runs in plain PyTorch and is about 3× slower under load
  (16 users: first audio ~2.4 s, 1–1.5 s of stutter). Check the server log for `Loaded flow-estimator TensorRT engine`.
- **Recommended: up to 16 concurrent users per GPU.**
- More GPUs: one instance per GPU (`GPU=1 PORT=8001 bash start.sh`, …) behind a load balancer; each WebSocket session
  stays on its instance, so capacity scales roughly linearly. CPU is not a bottleneck (~1.5 cores per instance at 16 users).

## API notes

- `/v1/chat/completions`: use the system prompt in `config/system_prompt.json` (the model was tuned with it; without it it
  uses far fewer sound tags), then the user audio as `input_audio`. Set `"modalities": ["text","audio"]`, optionally
  `"voice"` and `"language"`. Text deltas have tags removed; audio deltas are base64 WAV chunks (24 kHz). See `client_example.py`.
- `/v1/realtime`: OpenAI-Realtime-style session. Send `input_audio_buffer.append` continuously; put
  `"extra_body": {"auto_response": true, "language": "en"}` in `session.update`. The model decides turn-taking itself.

## What's inside

- `plugin/`: the vLLM-Omni plugin (`sophon_realtime`). Three stages: thinker (listens, writes, decides turns) → tag-tts
  talker (speech tokens, fed text while it is being written) → flow + HiFT vocoder (TensorRT, chunks of several users batched).
- `config/`: deploy config, system prompt, VAD model. `start.sh` turns on CUDA MPS so the three stages share the GPU.

License: Apache-2.0.
