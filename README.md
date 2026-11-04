<p align="center">
  <picture>
    <source media="(prefers-color-scheme: dark)" srcset="docs/assets/banner_dark.svg">
    <img src="docs/assets/banner_light.svg" alt="Sophon-Realtime — hears your tone, speaks with one. Open source on Nov 9, 2026" width="880">
  </picture>
</p>

<p align="center">
  <b>English</b> &nbsp;|&nbsp; <a href="README_CN.md">中文</a>
</p>

<h1 align="center">Hears your tone. Speaks with one.</h1>

<p align="center">
  <b>Sophon-Realtime is an open full-duplex voice model family: it listens while you talk, hears <i>how</i> you say things, and answers with a voice that carries tone of its own.</b>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/%F0%9F%9A%80%20Open%20source-Nov%209%2C%202026-22D3A6?style=for-the-badge" alt="Open source on Nov 9, 2026">
  <a href="https://github.com/adventists-ai/sophon-realtime/subscription"><img src="https://img.shields.io/badge/%F0%9F%94%94-Watch%20for%20release-181717?style=for-the-badge&logo=github" alt="Watch for release"></a>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/%F0%9F%A4%97%20Hugging%20Face-coming%20Nov%209-yellow" alt="Hugging Face: coming Nov 9">
  <img src="https://img.shields.io/badge/ModelScope-coming%20Nov%209-624aff" alt="ModelScope: coming Nov 9">
  <a href="LICENSE"><img src="https://img.shields.io/badge/license-Apache--2.0-blue" alt="Apache-2.0"></a>
</p>

> **🚀 Coming soon.** Weights, code and docs go live on **November 9, 2026 at 10:00 Beijing time** (13:00 Melbourne · Nov 8, 18:00 San Francisco).
> ⭐ **Star** this repo, or **Watch → Custom → Releases**, to be notified the moment it's out.

## What it is

Most voice agents turn your speech into text and lose everything else: the hesitation, the stress on one word, the laugh, the sigh. Sophon-Realtime keeps the audio in the loop, in both directions.

- **🎭 It has a human touch.** It hears emotion, emphasis, laughter and sighs straight from your voice, and it talks back with tone of its own: laughing, sighing, stressing the word that matters.
- **⚡ It's fast.** It listens the whole time you talk. Its voice starts about **0.3 s** into your pause, and you can cut in whenever you like.
- **🛠️ It gets work done.** Text and voice stream together, with the text half a step ahead. Every reply is a transcript you can audit, log and route to tools or a larger backend model.
- **🏠 You can run it yourself.** Apache-2.0 code and weights, serving on vLLM-Omni on your own GPU, and room to fine-tune for your product.

## Early numbers (preview builds)

| | |
|---|---|
| Voice starts after you stop talking | **≈ 0.3 s** |
| VoiceBench (spoken QA and reasoning) | **82.8** |
| Paralinguistic understanding (emotion, stress, laughter, sighs) | **#1 overall** on the open [DuplexJev](https://github.com/adventists-ai/duplexjev) benchmarks |

The full model lineup, benchmark tables and audio demos are published on release day.

## Arriving on November 9

- 🧠 Open weights on Hugging Face and ModelScope
- 📦 `pip install` package with a vLLM-Omni plugin: one command to serve
- 🎧 Browser demo: talk to it with your microphone
- 📖 Docs: quick start, deployment, fine-tuning

## From the same team

- **[DuplexJev](https://github.com/adventists-ai/duplexjev)**: one forward pass of a speech LLM answers every decision a voice agent needs (turn end, interruption, emotion, stress), in 92 ms.

## License

[Apache-2.0](LICENSE) for code and weights.

<p align="center"><sub>Sophon series · by <a href="https://github.com/adventists-ai">Adventists AI (AI降临派)</a></sub></p>
