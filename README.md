<p align="center">
  <img src="docs/assets/banner_v1_en.png" alt="Sophon-Realtime v1: hears your tone, speaks with one" width="880">
</p>

<p align="center">
  <b>English</b> &nbsp;|&nbsp; <a href="README_CN.md">中文</a>
</p>

<h1 align="center">Hears your tone. Speaks with one.</h1>

<p align="center">
  <b>Sophon-Realtime v1 is an open full-duplex voice model family: it listens while you talk, hears <i>how</i> you say things, and answers with a voice that laughs, sighs and breathes when the moment calls for it.</b>
</p>

<p align="center">
  <a href="https://huggingface.co/adventists-ai/Sophon-Realtime-32B-Tag"><img src="https://img.shields.io/badge/%F0%9F%A4%97%20Tag-Hugging%20Face-yellow" alt="Tag on Hugging Face"></a>
  <a href="https://huggingface.co/adventists-ai/Sophon-Realtime-32B-Flash"><img src="https://img.shields.io/badge/%F0%9F%A4%97%20Flash-Hugging%20Face-yellow" alt="Flash on Hugging Face"></a>
  <a href="https://www.modelscope.cn/models/AdventistsAI/Sophon-Realtime-32B-Tag"><img src="https://img.shields.io/badge/Tag-ModelScope-624aff" alt="Tag on ModelScope"></a>
  <a href="https://www.modelscope.cn/models/AdventistsAI/Sophon-Realtime-32B-Flash"><img src="https://img.shields.io/badge/Flash-ModelScope-624aff" alt="Flash on ModelScope"></a>
  <a href="https://www.modelscope.ai/studios/AdventistsAI/Sophon-Realtime"><img src="https://img.shields.io/badge/Try%20it-online-22D3A6" alt="Try it online"></a>
  <a href="LICENSE"><img src="https://img.shields.io/badge/license-Apache--2.0-blue" alt="Apache-2.0"></a>
</p>

## Demo

Real conversations with Sophon-Realtime, recorded as they happened: no edits, no speed-up. Turn the sound on.

https://github.com/user-attachments/assets/4d6c74f5-3bbf-4dc2-8b11-f90ff85de4a2

<details>
<summary>Chinese demo</summary>

https://github.com/user-attachments/assets/1d9442ef-84b0-45a3-acd4-2d05a9562397

</details>

## Highlights

- **VoiceBench 82.8 and Big Bench Audio 81.8%: the strongest brain among open full-duplex models.** #1 among open full-duplex models on both; level with GPT-4o-mini-Audio on VoiceBench. All three builds share this brain.
- **Paralinguistic understanding 48.6, #1 overall: it hears your tone.** Ahead of Gemini 3.8 Flash (46.9) and Qwen3-Omni (44.6) on LISTEN, StressTest and MSPB. It hears emotion, emphasis, sarcasm, laughter and sighs straight from your voice. Its ears are [DuplexJev](https://github.com/adventists-ai/duplexjev), our open speech-decision model.
- **NVV-SuperBench 0.86 (Chinese) and 0.80 (English) with the Tag build: it speaks with tone.** The model decides from the conversation when to laugh, sigh, breathe or clear its throat, and the voice performs it instead of reading the tag aloud.
- **Speaks your language: Chinese, English and five European languages, with more on the way.** Italian, German, Spanish, French and Portuguese work out of the box, Japanese and Russian run on Flash, and Korean is next. See [Languages](#languages).
- **Fast: first audio in about 0.25 s with E2E and 0.31 s with Flash.** It listens the whole time you talk and drafts its reply as you go. When you cut in, it stops and answers your new question.
- **Full-Duplex-Bench v3 tool calling: Pass@1 48%, ahead of Grok (43%), with a 100% response rate: it gets work done.** [Live mode](live/README.md) lets it work together with a larger backend model, and it is compatible with the OpenAI GPT-Live interface format. Every reply comes with an auditable transcript.
- **One 80 GB GPU for every build, one command.** Tag and Flash are served by vLLM-Omni; up to 16 (Tag, E2E) or 40 (Flash) concurrent users per GPU. Apache-2.0 code and weights, free for commercial use.

<p align="center">
  <img src="docs/assets/bench/voicebench_en.png" width="49%" alt="VoiceBench overall, full-duplex models">
  <img src="docs/assets/bench/bba_en.png" width="49%" alt="Big Bench Audio">
</p>
<p align="center">
  <img src="docs/assets/bench/fdb3_en.png" width="49%" alt="Full-Duplex-Bench v3 tool use, Pass@1">
  <img src="docs/assets/bench/paraling_en.png" width="49%" alt="Paralinguistic understanding, public benchmarks combined">
</p>
<p align="center">
  <img src="docs/assets/bench/nvv3_en.png" width="98%" alt="NVV-SuperBench, non-verbal sounds in speech, three builds">
</p>

<sub>Self-run unless noted. VoiceBench: official evaluators with a gpt-4o-mini judge; AlpacaEval on the standard 199-question subset. Big Bench Audio: GPT-4.1 judges the transcript of the spoken answer; other models from Artificial Analysis. Full-Duplex-Bench v3: best of several runs; other systems from the FDB v3 paper (Apr 2026). Paralinguistic understanding: same prompts and option rotation for every model. NVV-SuperBench: official prompts and metric, 50 items per class per language, Gemini 3 Flash judge; the three builds speak the same tagged reply texts in the Chelsie voice. Latency and concurrency: one H100 80 GB, users arriving within 10 s.</sub>

## News

- **2026-11-11 · v1.1: zero-shot voice cloning** in the Tag and Flash builds. A few seconds of audio and it talks to you in that voice, in real time. [Watch the demo](#zero-shot-voice-cloning-new-in-v11)
- **2026-11-12 · 1.1.5:** restarts no longer recompile kernels when several installs share a machine; every part of the family now carries the same version. See the [changelog](CHANGELOG.md).
- **2026-11-12 · 1.1.4: E2E can also be served by vLLM-Omni**, with the same commands, APIs and client as Tag and Flash. [`e2e/`](e2e/README.md)
- **2026-11-11 · 1.1.3: E2E joins Tag and Flash as a full build, on one GPU.** New talker, first audio in about 0.25 s, 16 users per 80 GB GPU, NVV-SuperBench 0.75 (English) / 0.85 (Chinese). [Details](#e2e)
- **2026-11-11 · 1.1.2:** `sophon-realtime serve` turns on CUDA MPS by default; long-reply and cold-start fixes. See the [changelog](CHANGELOG.md).
- **2026-11-08 · v1.0:** first public release of the Tag, Flash and E2E (preview) builds.

## Three builds, one brain

All three builds share the same brain: one 32B model that listens to your voice, decides when you have finished, and writes the reply. They differ only in **how the reply becomes sound**.

| | **Tag** (recommended) | **Flash** | **E2E** |
|---|---|---|---|
| How it speaks | The brain writes the reply with sound tags (`[laughter]`, `[sigh]`, `<strong>…</strong>` …); an expressive speech model performs them | Same tagged reply, spoken by a lighter, faster speech model (one forward pass per 80 ms frame) | No speech-token model: a compact talker (about 350M parameters) reads the tagged reply as it is written and generates continuous voice vectors directly; a decoder turns them into sound |
| Best for | Expressive voice: companions, characters, demos | Speed and scale: customer service, in-car, many users per GPU | Expressive voice with the fastest first audio; our own engine, easy to modify |
| Non-verbal sounds (NVV-SuperBench, en / zh) | **0.80 / 0.86** | 0.63 / 0.77 | 0.75 / 0.85 |
| First audio, one user | ~0.6 s | 0.31 s | **~0.25 s** |
| Users per 80 GB GPU (recommended) | 16 | **40** | 16 |
| Zero-shot voice cloning | **yes**, from a 3–10 s clip ([how](tag/README.md#zero-shot-voice-cloning)) | **yes**, from a 3–10 s clip ([how](flash/README.md#zero-shot-voice-cloning)) | no |
| GPUs | **1** × 80 GB | **1** × 80 GB | **1** × 80 GB |
| Serving | vLLM-Omni, one command | vLLM-Omni, one command | own engine or vLLM-Omni, one command |
| Weights | [HF](https://huggingface.co/adventists-ai/Sophon-Realtime-32B-Tag) · [ModelScope](https://www.modelscope.cn/models/AdventistsAI/Sophon-Realtime-32B-Tag) | [HF](https://huggingface.co/adventists-ai/Sophon-Realtime-32B-Flash) · [ModelScope](https://www.modelscope.cn/models/AdventistsAI/Sophon-Realtime-32B-Flash) | [HF](https://huggingface.co/adventists-ai/Sophon-Realtime-32B-E2E) · [ModelScope](https://www.modelscope.cn/models/AdventistsAI/Sophon-Realtime-32B-E2E) |
| Code | [`tag/`](tag/README.md) | [`flash/`](flash/README.md) | own engine: [`docs/deploy.md`](docs/deploy.md) · vLLM-Omni: [`e2e/`](e2e/README.md) |

**Which one?** Start with **Tag** if you want the voice to act. Pick **Flash** if the number of users per GPU matters most. Pick **E2E** for the fastest first audio with a voice that still laughs and sighs. Tag and Flash share the same APIs, so you can switch later; E2E runs on its own engine or, since 1.1.4, on vLLM-Omni with the same APIs as Tag and Flash.

## Languages

Talk to it in your own language. Sophon-Realtime listens and answers in the language you speak.

| Language | Status |
|---|---|
| Chinese, English | Fully supported |
| Italian, German, Spanish, French, Portuguese | Ready for conversation: clear speech, 80–92% of basic questions answered correctly, multi-turn quality close to English |
| Japanese, Russian | Available on the Flash build |
| Korean and more | Coming soon |

<sub>Internal tests, November 2026: 15 languages × 20 spoken questions, plus multi-turn dialogues from Omnilingua-AudioMC in 8 languages (Portuguese not included). Japanese is a priority language for us, and upcoming releases will keep improving it.</sub>

## How it works

- **Listens continuously.** At each pause, the same model decides in a single token whether you've finished, are still talking, are back-channeling or are thinking.
- **Drafts early, speaks on time.** A reply is drafted from your first pause and released the moment the model decides it's its turn. If you keep talking, the draft is dropped before you hear it.
- **Writes how to say it, not just what.** The brain marks where to laugh, sigh, breathe, cough or stress a word. Tag and Flash perform these marks; they are never read aloud.
- **Barge-in.** When you interrupt, it stops and keeps only the part you actually heard in the conversation history.

## Quick start

**Quickest** (Tag build, one 80 GB GPU):

```bash
pip install "sophon-realtime[trt]"   # Python 3.12, Linux, CUDA 13; installs vLLM-Omni, the Tag plugin and TensorRT
sophon-realtime serve           # downloads Sophon-Realtime-32B-Tag (~42 GB) on first run, then serves on port 8000
```

> **Keep the `[trt]`.** Without TensorRT the voice runs in plain PyTorch and is about 3× slower under load (16 users: first audio ~2.4 s
> instead of ~0.75 s, with 1–1.5 s of stutter). `sophon-realtime serve` now warns at start-up when TensorRT is missing.

Or use the one-command scripts, which set up an isolated environment:

**Tag** (one 80 GB GPU):

```bash
git clone https://github.com/adventists-ai/sophon-realtime && cd sophon-realtime/tag
bash install.sh                 # venv + vLLM-Omni + plugin, downloads the weights (~45 GB)
GPU=0 PORT=8000 bash start.sh
python client_example.py --wav my_question.wav --lang en
```

**Flash** (one 80 GB GPU):

```bash
cd sophon-realtime/flash
bash install.sh
modelscope download --model AdventistsAI/Sophon-Realtime-32B-Flash --local_dir ./model   # or: hf download adventists-ai/Sophon-Realtime-32B-Flash --local-dir ./model
GPU=0 PORT=8000 bash start.sh
python client_example.py --wav my_question.wav --lang en --voice chelsie
```

Both serve `ws://HOST:PORT/v1/realtime` (full duplex, OpenAI-Realtime-style) and `POST /v1/chat/completions` (audio in, text + audio out). Details: [tag/README.md](tag/README.md) · [flash/README.md](flash/README.md).

**Optional: Live mode** (OpenAI GPT-Live compatible, see [live/](live/README.md)), next to a running engine:

```bash
cd sophon-realtime/live && BUILD=tag PORT=8000 LIVE_PORT=8780 bash start_live.sh   # GPT-Live clients: ws://HOST:8780/v1/live/sessions
```

## Live mode (OpenAI GPT-Live compatible)

[`live/`](live/README.md) is a gateway that speaks the OpenAI GPT-Live protocol in front of a Tag or Flash engine: GPT-Live clients switch by changing the URL and key. Sophon keeps the voice and hands lookups and actions to your backend through delegation, then speaks the result. Optionally, a larger model can run the back office.

## Zero-shot voice cloning (new in v1.1)

Give Sophon a few seconds of someone's voice and it talks to you in that voice, in real time. No fine-tuning, no restart, one GPU. Works in the Tag and Flash builds.

https://github.com/user-attachments/assets/7f0627b0-fae4-4633-b412-88cb24942ab8

```bash
pip install -U "sophon-realtime[trt]"
sophon-realtime download --source modelscope   # or Hugging Face (default)
cp alice.wav model/voices/                      # 3-10 s, one speaker
sophon-realtime serve                           # then set "voice": "alice"
```

New, replaced and deleted voices take effect on the next request. Barge-in, backchannels and laughs still work in a cloned voice, and a voice cloned from one language can speak another. Everything stays on your server ([details](tag/README.md#zero-shot-voice-cloning)). The video also shows [Live mode](live/README.md): Sophon hands lookups (weather, news) to your own backend, keeps talking, then says the answer.

**Please only clone your own voice or voices you have permission to use. Do not use it to impersonate anyone or to deceive.**

<details>
<summary>Chinese-subtitled version</summary>

https://github.com/user-attachments/assets/74bd6096-b6fc-4433-a1d7-d3e967107193

</details>

## E2E

The E2E build has no speech-token model in the middle. A compact talker (about 350M parameters) reads the brain's tagged reply while it is still being written and generates a stream of continuous voice vectors, about 6.5 frames per second; a 2-step decoder and a vocoder turn them into 24 kHz audio. Laughs, coughs, sighs, breaths and stressed words are produced by the talker itself, as part of the same stream. Everything runs on **one 80 GB GPU** with our own engine: [docs/deploy.md](docs/deploy.md). Weights: [HF](https://huggingface.co/adventists-ai/Sophon-Realtime-32B-E2E) · [ModelScope](https://www.modelscope.cn/models/AdventistsAI/Sophon-Realtime-32B-E2E).

Measured from a fresh install on one H100: first audio for one user in about 0.25 s; 16 users arriving within 10 s get first audio in 0.44 s (median) / 0.56 s (P90) with no reply falling behind playback. NVV-SuperBench: 0.75 (English) / 0.85 (Chinese). Full table in [docs/deploy.md](docs/deploy.md#performance-one-h100-80-gb-measured-from-a-fresh-install). This build speaks Chinese and English with one built-in voice; for voice cloning or more languages use Tag or Flash.

E2E can be served in two ways, with the same weights and the same voice: by our own engine ([docs/deploy.md](docs/deploy.md), the numbers above), or as one vLLM-Omni model like Tag and Flash ([e2e/](e2e/README.md): `/v1/realtime` and `/v1/chat/completions`; first audio about 0.35 s for one user and 0.58–0.65 s (median) for 16). Both are measured on an H100. The E2E voice stages run about 2× slower on an RTX PRO 6000 (about 4–8 users per GPU); on such cards use Tag or Flash if you need more users per GPU.

## Fine-tuning

Adapt the brain (persona, tone, domain knowledge, tool use) with LoRA in [ms-swift](https://github.com/modelscope/ms-swift) on one 80 GB GPU. The voice, expressive sound tags and turn-taking are kept. See [finetune/](finetune/README.md).

## From the same team

- **[DuplexJev](https://github.com/adventists-ai/duplexjev)**: one forward pass of a speech LLM answers every decision a voice agent needs (turn end, interruption, emotion, stress), in 92 ms.

## License

[Apache-2.0](LICENSE) for code and weights. See each build's `NOTICE` for third-party components.

<p align="center"><sub>Sophon series · by <a href="https://github.com/adventists-ai">Adventists AI</a></sub></p>
