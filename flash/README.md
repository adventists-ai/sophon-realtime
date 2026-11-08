# Sophon-Realtime-32B-Flash: one GPU, one command (vLLM-Omni)

A full-duplex speech model served as **one** vLLM-Omni model: it listens to the user, writes a reply (optionally with sound tags `[laughter]` `[cough]`
`[sigh]` `[breath]` `<laughter>…</laughter>` `<strong>…</strong>`), and speaks while it writes. The voice stage emits one frame every 80 ms; tags are
performed, never read aloud.

Flash shares the tag-writing thinker with the Tag build; only the voice stage differs. Flash's voice stage is autoregressive with a single forward pass per
step, so **first audio is faster and concurrency is higher**; the Tag build laughs more convincingly. Both have the same API.

## Performance (one H100 80 GB, FP8 thinker, `/v1/chat/completions`, user speech → first audio chunk)

| Load | First audio median / P90 | Stall (median) |
|---|---|---|
| 1 stream | **0.31 / 0.34 s** | 0 |
| 20 streams (arriving over 10 s) | 0.45 / 0.52 s | 0.09 s |
| 40 streams (over 10 s) | 0.58 / 0.67 s | 0.37 s |
| 64 streams (over 8 s) | 0.84 / 1.03 s | 1.9 s (queueing) |

- **Up to about 40 concurrent streams per 80 GB GPU is recommended.** For more, run one instance per GPU behind a load balancer.
- Memory: about 55 GB per instance. The first start compiles kernels (about 10 min); later starts take 5–8 min.

### Sound tags (held-out set, Chelsie voice, judged by DuplexJev)

| Tag | zh | en |
|---|---|---|
| `[laughter]` | 83% | 77% |
| `<laughter>…</laughter>` laughing while speaking | 78% | 71% |
| `[cough]` | 90% | 50% (8 items) |
| `[sigh]` (AST) | 90% | 100% |
| Mean character / word error rate | 0.9% | 1.0% |

- Tags are never read aloud; without a tag the model rarely laughs on its own.
- `<strong>` emphasis is still weak in this build; the next build will improve it.

## Quick start

```bash
bash install.sh                 # once: Python 3.12 venv, vLLM 0.30, vLLM-Omni 0.30, plugin
# put the weights in ./model (ModelScope: modelscope download --model AdventistsAI/Sophon-Realtime-32B-Flash --local_dir ./model)
GPU=0 PORT=8000 bash start.sh
python client_example.py --wav my_question.wav --lang en --voice chelsie
bash stop.sh
```

Voices: `chelsie` (default), `brand`; set `language` to `zh` or `en`.

## API
- `/v1/chat/completions`: use the system prompt in `config/system_prompt.json` (the model was tuned with it; without it fewer tags are written); put the
  user's speech in `input_audio`; `"modalities": ["text","audio"]`, optional `"voice"` and `"language"`. The text stream keeps the tags (strip them for
  display if you like); the audio stream is base64 WAV chunks (24 kHz).
- `/v1/realtime`: OpenAI Realtime-style session; keep sending `input_audio_buffer.append`; the model decides when the user has finished.

## Layout
`model/` (thinker, voice stage, voices) · `plugin/` (vLLM-Omni plugin `sophon_realtime`) · `config/` (deploy config, system prompt, VAD) · `examples/`

License: code Apache-2.0; model weights Apache-2.0, see `NOTICE` for sources.
