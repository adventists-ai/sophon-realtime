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
  <a href="LICENSE"><img src="https://img.shields.io/badge/license-Apache--2.0-blue" alt="Apache-2.0"></a>
</p>

## Highlights

- **VoiceBench 82.8 and Big Bench Audio 81.8%: the strongest brain among open full-duplex models.** #1 among open full-duplex models on both; level with GPT-4o-mini-Audio on VoiceBench. All three builds share this brain.
- **Paralinguistic understanding 48.6, #1 overall: it hears your tone.** Ahead of Gemini 3.8 Flash (46.9) and Qwen3-Omni (44.6) on LISTEN, StressTest and MSPB. It hears emotion, emphasis, sarcasm, laughter and sighs straight from your voice. Its ears are [DuplexJev](https://github.com/adventists-ai/duplexjev), our open speech-decision model.
- **NVV-SuperBench 0.86 (Chinese) and 0.80 (English) with the Tag build: it speaks with tone.** The model decides from the conversation when to laugh, sigh, breathe or clear its throat, and the voice performs it instead of reading the tag aloud.
- **Fast: first audio in 0.31 s with Flash.** It listens the whole time you talk and drafts its reply as you go. When you cut in, it stops and answers your new question.
- **Full-Duplex-Bench v3 tool calling: Pass@1 48%, ahead of Grok (43%), with a 100% response rate: it gets work done.** [Live mode](live/README.md) lets it work together with a larger backend model, and it is compatible with the OpenAI GPT-Live interface format. Every reply comes with an auditable transcript.
- **One 80 GB GPU, one command (Tag and Flash).** Served by vLLM-Omni; up to 16 (Tag) or 40 (Flash) concurrent users per GPU. Apache-2.0 code and weights, free for commercial use.

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

## Three builds, one brain

All three builds share the same brain: one 32B model that listens to your voice, decides when you have finished, and writes the reply. They differ only in **how the reply becomes sound**.

| | **Tag** (recommended) | **Flash** | **E2E** (preview) |
|---|---|---|---|
| How it speaks | The brain writes the reply with sound tags (`[laughter]`, `[sigh]`, `<strong>…</strong>` …); an expressive speech model performs them | Same tagged reply, spoken by a lighter, faster speech model (one forward pass per 80 ms frame) | No separate speech model: a talker inside the 32B model turns the reply into continuous voice vectors, and a decoder turns them into sound |
| Best for | Expressive voice: companions, characters, demos | Speed and scale: customer service, in-car, many users per GPU | Research on end-to-end expressive speech |
| Non-verbal sounds (NVV-SuperBench, en / zh) | **0.80 / 0.86** | 0.63 / 0.77 | 0.60 / 0.77 |
| First audio, one user | ~0.6 s | **0.31 s** | ~1 s |
| Users per 80 GB GPU (recommended) | 16 | **40** | 4–5 (speaking engine) |
| GPUs | **1** × 80 GB | **1** × 80 GB | 2 × 80 GB |
| Serving | vLLM-Omni, one command | vLLM-Omni, one command | own engine |
| Weights | [HF](https://huggingface.co/adventists-ai/Sophon-Realtime-32B-Tag) · [ModelScope](https://www.modelscope.cn/models/AdventistsAI/Sophon-Realtime-32B-Tag) | [HF](https://huggingface.co/adventists-ai/Sophon-Realtime-32B-Flash) · [ModelScope](https://www.modelscope.cn/models/AdventistsAI/Sophon-Realtime-32B-Flash) | [HF](https://huggingface.co/adventists-ai/Sophon-Realtime-32B-E2E) · [ModelScope](https://www.modelscope.cn/models/AdventistsAI/Sophon-Realtime-32B-E2E) |
| Code | [`tag/`](tag/README.md) | [`flash/`](flash/README.md) | [`docs/deploy.md`](docs/deploy.md) |

**Which one?** Start with **Tag** if you want the voice to act. Pick **Flash** if latency and the number of users per GPU matter most. Same APIs, so you can switch later.

## How it works

- **Listens continuously.** At each pause, the same model decides in a single token whether you've finished, are still talking, are back-channeling or are thinking.
- **Drafts early, speaks on time.** A reply is drafted from your first pause and released the moment the model decides it's its turn. If you keep talking, the draft is dropped before you hear it.
- **Writes how to say it, not just what.** The brain marks where to laugh, sigh, breathe, cough or stress a word. Tag and Flash perform these marks; they are never read aloud.
- **Barge-in.** When you interrupt, it stops and keeps only the part you actually heard in the conversation history.

## Quick start

**Quickest** (Tag build, one 80 GB GPU):

```bash
pip install sophon-realtime     # Python 3.12, Linux, CUDA; installs vLLM-Omni and the Tag plugin
sophon-realtime serve           # downloads Sophon-Realtime-32B-Tag (~42 GB) on first run, then serves on port 8000
```

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

## E2E (preview)

The E2E build speaks without a separate speech model. While the 32B model listens, it builds a stream of continuous vectors that carries both what was said and how; the E2E talker writes replies in that same vector language and a decoder turns it into sound, so hearing and speaking share one representation. It runs on two 80 GB GPUs with our own engine ([docs/deploy.md](docs/deploy.md)). Weights: [HF](https://huggingface.co/adventists-ai/Sophon-Realtime-32B-E2E) · [ModelScope](https://www.modelscope.cn/models/AdventistsAI/Sophon-Realtime-32B-E2E).

**New build (Nov 2026): upgraded decoder, 4 steps.** Same compute per audio chunk as before. On replies from the same talker:

| | previous decoder | new decoder |
|---|---|---|
| Long replies, error rate (150 replies, zh / en / ja) | 1.78% (1.03 / 1.32 / 2.99) | **1.51% (0.97 / 0.71 / 2.86)** |
| Voice similarity to an unseen reference speaker | 0.33 | **0.52** |

The previous weights stay in [Sophon-Realtime-v1](https://huggingface.co/adventists-ai/Sophon-Realtime-v1).

## Fine-tuning

Adapt the brain (persona, tone, domain knowledge, tool use) with LoRA in [ms-swift](https://github.com/modelscope/ms-swift) on one 80 GB GPU. The voice, expressive sound tags and turn-taking are kept. See [finetune/](finetune/README.md).

## From the same team

- **[DuplexJev](https://github.com/adventists-ai/duplexjev)**: one forward pass of a speech LLM answers every decision a voice agent needs (turn end, interruption, emotion, stress), in 92 ms.

## License

[Apache-2.0](LICENSE) for code and weights. See each build's `NOTICE` for third-party components.

<p align="center"><sub>Sophon series · by <a href="https://github.com/adventists-ai">Adventists AI</a></sub></p>
