# Changelog

One version number for the whole Sophon-Realtime v1 family: the code in this repository (Tag, Flash, E2E, Live), the weights on Hugging Face /
ModelScope (git tags with the same name) and the `sophon-realtime` package on PyPI. Each entry says which builds changed.
Second digit: new features or new weights; third digit: fixes only.

## 1.1.5 (2026-11-12): faster restarts, READY means ready, one version number everywhere

- Fix (Tag, Flash, E2E; `sophon-realtime serve`): every start could spend several extra minutes compiling kernels again. vLLM keeps its compiled kernels in `~/.cache/flashinfer`, one cache for all vLLM installs of a user, and installs with different paths overwrite each other's build there, so with more than one install on a machine (for example `tag/` and `flash/`, or two virtual environments) each start rebuilt them. The start scripts now keep the cache inside the install directory (`FLASHINFER_WORKSPACE_BASE`; `sophon-realtime serve` keeps it in the virtual environment). Measured with the E2E vLLM-Omni build on a machine with several installs: every start 12 min before, about 6 min for the first start and 4.5 min afterwards now. The 1.1.4 E2E scripts already had this.
- Fix (Tag, Flash, E2E start scripts): `start.sh` printed READY while the server was still warming itself up in the background (a throwaway realtime session of about 20 s), so a request sent right after READY could take 8–12 s to its first audio. `start.sh` now waits for that warm-up to finish before it prints READY. `sophon-realtime serve` has no READY message: give it about 30 s after it starts answering.
- All parts now carry the same version, 1.1.5: the Tag, Flash and E2E plugins, the own engine and `sophon-realtime` on PyPI (they were at 1.1.2, 1.1.3 or 1.1.4).
- No weight changes: Tag and Flash weights stay at 1.1.0, E2E at 1.1.4.

## 1.1.4 (2026-11-12): E2E on vLLM-Omni

- **E2E can now be served as one vLLM-Omni model** ([`e2e/`](e2e/README.md)), with the same `install.sh` / `start.sh`, the same `/v1/realtime` and `/v1/chat/completions` APIs and the same client as Tag and Flash. The talker and the decoder are the engine from 1.1.3, wrapped as two vLLM-Omni stages; the talker output is bit-identical to the own engine's. The own engine (`scripts/`, [docs/deploy.md](docs/deploy.md)) stays and is still a little faster.
- Measured on one H100 from the release package (spoken question in, spoken answer out, users arriving within 10 s): first audio about 0.35 s for one user (own engine: 0.25 s); 16 users 0.58–0.65 s median / 0.71–0.87 s P90 with 0–2 replies more than 0.3 s behind playback (own engine: 0.44 / 0.56 s, none); 16 users × 5 turns 0.64 / 0.84–0.91 s. `/v1/realtime`: about 0.45 s from the end of speech to the first voice. Replies of 80–128 s of speech play to the end; one reply is spoken for at most about 2 to 2.5 minutes and then ends at a sentence end (the talker stays accurate up to about 150 s of continuous speech). Cancelled requests free their slot at once.
- **Hardware note for E2E:** the numbers are for the H100 class. On an RTX PRO 6000 (Blackwell, 96 GB) the vLLM-Omni build installs and runs, but one GPU keeps up with about 4–8 concurrent users: the voice stages run about 2× slower there. The own engine uses the same voice stages; we have not measured it on that card. Tag and Flash reach 16 users on the same card.
- In the vLLM-Omni build the vocoder graphs are captured with cuDNN choosing the convolution algorithms by timing (at start-up only). On RTX PRO 6000 this makes the vocoder about 4× faster; on H100 it changes little. `SOPHON_E2E_CUDNN_BENCHMARK=0` turns it off.
- E2E weights on Hugging Face and ModelScope (tag `v1.1.4`): added `thinker/` (the thinker with the reply LoRA merged in, FP8, about 36 GB; the same files as in the Tag repository), `config.json` and `talker220/config.json` for the vLLM-Omni deployment. Nothing else changed. `scripts/install.sh` now skips `thinker/`, so the own-engine download keeps its size.
- Tag, Flash and Live are unchanged; `sophon-realtime` on PyPI stays at 1.1.2.

## 1.1.3 (2026-11-11): E2E out of preview, on one GPU

- **E2E is no longer a research preview and now runs on one 80 GB GPU** (it needed two). New talker (about 350M parameters) that reads the tagged reply and generates continuous voice vectors directly, a 2-step decoder, and a new speaking engine that batches every conversation in one loop. The thinker and the speaking engine share the GPU through CUDA MPS, which `scripts/start.sh` starts and `scripts/stop.sh` stops.
- Measured from a fresh install on one H100 (spoken question in, spoken answer out): first audio for one user about 0.25 s (was about 1 s); 16 users arriving within 10 s get first audio in 0.44 s median / 0.56 s P90 with no reply falling more than 0.3 s behind playback (the preview was recommended for 4–5 users on its own GPU). Full table, including 24 and 32 users and sustained multi-turn load, in [docs/deploy.md](docs/deploy.md).
- NVV-SuperBench (official prompts and metric, Gemini 3 Flash judge): English 0.75, Chinese 0.85 (preview: 0.60 / 0.77).
- Sound tags of the E2E talker: `[laughter]`, `[cough]`, `[sigh]`, `[breath]`, `<strong>…</strong>` and `<laughter>…</laughter>` (speaking while laughing). It also accepts `[cry]`, `[clear]` and `[gasp]`; these three are not benchmarked yet and the thinker does not write them on its own.
- Length guards: one reply is at most about 4.6 minutes of speech (about 960 text tokens). A longer reply ends cleanly there; an error in one conversation no longer affects the others. Tested with 4,000 characters without punctuation, in Chinese and English, next to normal requests.
- E2E weights updated on Hugging Face and ModelScope (tagged `v1.1.3`): new `talker220/`, `talker/` removed (the download is about 8 GB smaller). `base/`, `adapters/`, `e2/` and `voices/` are unchanged. The preview weights stay at tag `v1.1.0`; use them with code tag `v1.1.2`.
- `scripts/start.sh` changed: `GPU=0` instead of `THINKER_GPU` / `TALKER_GPU`; new `SLOTS`, `MPS`, `THINKER_MEM`.
- Fix: `scripts/install.sh` failed on a clean machine because the constraint files pinned `setuptools` and `pip` to versions that conflict with vLLM 0.29. The pins are removed.
- This E2E build speaks Chinese and English with one built-in voice; voice cloning stays in Tag and Flash.
- Tag, Flash and Live are unchanged; `sophon-realtime` on PyPI stays at 1.1.2.

## 1.1.2 (2026-11-11): `sophon-realtime serve` uses CUDA MPS

- `sophon-realtime serve` now runs the three stages through CUDA MPS on the GPU, as `tag/start.sh` always did. Before, they time-sliced the GPU: with 16 concurrent long replies each session got about 120 s of speech in a 170 s window (slower than real time, so listeners heard pauses); with MPS about 200 s (faster than real time), and first audio drops too. `SOPHON_MPS=0` turns it off; without the MPS tools it falls back to the old behaviour with a note.
- Re-qualified from a fresh `pip install "sophon-realtime[trt]"` and freshly downloaded weights on one H100, with the protocol from [HF discussion #1](https://huggingface.co/adventists-ai/Sophon-Realtime-32B-Tag/discussions/1): first realtime session after a cold start answered; 16 short requests at concurrency 1 / 4 / 8 / 16; long replies serially (up to 11 min of speech) and 16 concurrent with 163.84 s of silence for 4 consecutive batches plus a fresh session, then again after a fresh restart. No rejected TensorRT shapes, no stage crash, no server-side error or unexpected session end.
- `sophon-realtime` 1.1.2 on PyPI. No weight changes (weights stay at 1.1.0).

## 1.1.1 (2026-11-11): TensorRT install fix

- Fix: `pip install "sophon-realtime[trt]"` failed with pip. TensorRT 10.13 depends on the deprecated `nvidia-cuda-runtime-cu13`, whose default release cannot be built. The `[trt]` extra now pins the one installable release (`0.0.0a0`). Tested from a fresh Python 3.12 venv with plain pip: TensorRT installs, the voice runs on TensorRT, 16 users get first audio in about 1 s. `tag/install.sh` was not affected.
- `tag/install.sh` and `tag/start.sh` now print a clear warning when TensorRT is missing or off, instead of continuing silently.
- `sophon-realtime` 1.1.1 on PyPI. No weight changes (weights stay at 1.1.0).

## 1.1.0 (2026-11-11): zero-shot voice cloning (Tag, Flash), new Tag voice model

- Flash: zero-shot voice cloning ([#2](https://github.com/adventists-ai/sophon-realtime/issues/2)). Put a 3-10 s clip at `model/voices/<name>.wav` and use `"voice": "<name>"` in `/v1/chat/completions` or `/v1/realtime`; no fine-tuning or restart. Voices are re-read when the file changes, and an unknown or unreadable voice falls back to `chelsie` with a warning instead of failing the request. See [flash/README.md](flash/README.md#zero-shot-voice-cloning).
- Tag: zero-shot voice cloning ([#2](https://github.com/adventists-ai/sophon-realtime/issues/2)). Put a 3-10 s clip at `model/voices/<name>.wav` and use `"voice": "<name>"` in `/v1/chat/completions` or `/v1/realtime`; no fine-tuning or restart. New clips are prepared in the background (the voices folder is scanned every 5 s), so first audio is as fast as with a built-in voice. Unknown or unreadable voices fall back to `chelsie` with a warning. See [tag/README.md](tag/README.md#zero-shot-voice-cloning).
- Tag weights updated on Hugging Face and ModelScope (tagged `v1.1.0`): new `talker/flow.pt` and `talker/flow.decoder.estimator.fp32.onnx`. Unseen voices sound much closer to the reference; built-in voices, sound tags, intelligibility and speed are unchanged. The TensorRT engine is rebuilt automatically on the first start after the update.
- **TensorRT matters.** `pip install sophon-realtime` without `[trt]` runs the voice in plain PyTorch, about 3x slower under load (16 users: first audio ~2.4 s instead of ~0.75 s). The README now says `pip install "sophon-realtime[trt]"`, and `sophon-realtime serve` warns at start-up when TensorRT is missing.
- `sophon-realtime` 1.1.0 on PyPI with these changes (`pip install -U "sophon-realtime[trt]"`); 1.0.5, published earlier the same day, has the same code.

## 1.0.4 (2026-11-11): hard guard for long requests (Tag)

- Tag build, a hard guard that does not depend on segmenting: the flow decoder now only sees the last part of a long request (at most 2,800 mel frames with the prompt, `SOPHON_FLOW_MAX_FRAMES`; at least 50 tokens of context before the new audio, `SOPHON_FLOW_CTX_TOKENS`). If a flow call still fails, only that request loses that audio chunk; the stage and the other sessions keep running.
- Tested on one H100 with segmenting and the HTTP speech cap both switched off, so every reply ran into the old limit: 16 concurrent realtime sessions with 4,096-token replies plus 4 concurrent long HTTP requests ran with no TensorRT errors, and a fresh session afterwards answered normally. With the default settings: 32 concurrent long sessions with half of them dropping their connection abruptly mid-reply, replies without any punctuation, and Chinese and English replies over 3 minutes all ran without errors.

## 1.0.3 (2026-11-11): long replies (Tag)

- Fix: on the Tag build, a very long spoken reply (over about 60 s of audio, e.g. a session with a large `max_response_output_tokens`) could crash the TensorRT flow stage and end every open session ([HF discussion #1](https://huggingface.co/adventists-ai/Sophon-Realtime-32B-Tag/discussions/1), thanks to Trelis Research). The streaming flow decoder re-runs over the whole reply, so a long reply went past the TensorRT engine's 3000-frame profile.
- Realtime sessions now speak long replies in segments: the model writes about 120 tokens at a time, each segment ends at a sentence end, and the next one starts at once while the previous is still playing, with no gap. Each segment is short enough for the engine, so a reply has no length limit other than the session's token budget. Segment size: `SOPHON_SEG_TOKENS` (0 turns segmenting off).
- Requests that are not segmented (HTTP `/v1/chat/completions` with a large `max_tokens`) now end their speech at a sentence end before 50 s (`SOPHON_MAX_SPEECH_S`); the text reply is not cut.
- If the flow engine still fails on a batch, it now retries the requests one at a time instead of stopping the stage.
- Idle realtime sessions are kept for 300 s instead of 60 s (`idle_ttl_s`).
- Tested with Trelis Research's protocol: 16 concurrent `/v1/realtime` sessions, 80 ms float32 16 kHz frames in real time, a spoken prompt and then 163.84 s of silence, 4 batches plus a fresh session, from a fresh restart: 65 of 65 sessions completed, replies up to 288 s of audio, longest segment 41 s, no errors. First-audio latency for short replies is unchanged (about 0.35 s alone, 1.1-1.5 s at 8 and 2.1-2.4 s at 16 concurrent sessions on one H100).
- `sophon-realtime` 1.0.3 on PyPI with these changes (`pip install -U sophon-realtime`). Flash replies already reach about 160 s without this problem; the E2E build has not been tested for very long replies.

## 1.0.2 (2026-11-11): lost first realtime reply after a cold start (Tag, Flash)

- Fix: on the Tag build, the first realtime (`/v1/realtime`) session after a cold start could end with no reply, while HTTP inference worked ([HF discussion #1](https://huggingface.co/adventists-ai/Sophon-Realtime-32B-Tag/discussions/1), thanks to Trelis Research). A reply append that the framework did not accept in time was dropped for good. It is now rolled back and sent again; a speculative draft that never reached the engine is no longer treated as released; the unconfirmed-append timeout is 15 s instead of 2 s (`SOPHON_RES_TIMEOUT`).
- The server now warms itself up once it is ready: three turn questions plus one short throwaway realtime session (about 20 s), so the first real session is as fast as later ones. Set `SOPHON_WARMUP=0` to skip.
- `sophon-realtime` 1.0.2 on PyPI with these fixes (`pip install -U sophon-realtime`). The Flash plugin (`flash/plugin`) has the same fix and warm-up, tested the same way on a Flash instance.

## 1.0.1 (2026-11-09)

- `sophon-realtime` 1.0.1 on PyPI: `sophon-realtime serve` now serves the model under the name `adventists-ai/Sophon-Realtime-32B-Tag` (alias `sophon-realtime`).
- Live mode: LiveKit Agents and Pipecat examples for the OpenAI Realtime compatible endpoint (`live/examples/`), tested with livekit-agents 1.8.11 and Pipecat v1.15.0.

## 1.0.0 (2026-11-08): first public release

- First public release of the Sophon-Realtime v1 family: Sophon-Realtime-32B-Tag, Sophon-Realtime-32B-Flash and Sophon-Realtime-32B-E2E (research preview).
- One-command install and start scripts for Tag and Flash (vLLM-Omni, one 80 GB GPU), `pip install sophon-realtime`.
- Live mode: GPT-Live and OpenAI Realtime compatible gateway (`live/`).
