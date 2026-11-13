# Sophon Realtime on Mac (Apple silicon)

Talk to Sophon-Realtime-32B-Flash-4bit **locally on a Mac**. It is full duplex: you can interrupt it, it decides for itself when you have finished
speaking, and "mm-hmm" while it talks lets it carry on. Hearing, turn-taking and speaking are all done by the model itself on the Mac's GPU (MLX):
no cloud, and no speech-to-text step in between.

## Requirements
- Mac with Apple silicon (M1 or later), macOS 14 or later
- **36 GB or more unified memory recommended**; 32 GB works if other apps are closed (the model uses about 26 GB while talking)
- About 30 GB free disk (the model is about 24 GB)
- A microphone. Mac Studio and Mac mini have none built in, so plug in a USB microphone or a headset. Speakers are fine: echo cancellation is built in

## Install (one command)
```bash
bash mac/install.sh
```
The installer sets up its own Python environment in `~/sophon-mac` and downloads
[Sophon-Realtime-32B-Flash-4bit-MLX](https://huggingface.co/adventists-ai/Sophon-Realtime-32B-Flash-4bit-MLX) once (about 24 GB; from ModelScope
with Chinese package mirrors when Hugging Face is not reachable). Those are the Flash-4bit weights repacked losslessly for MLX; if you already have
the CUDA repo [Sophon-Realtime-32B-Flash-4bit](https://huggingface.co/adventists-ai/Sophon-Realtime-32B-Flash-4bit), `convert.py SRC DST`
produces the same files from it in about a minute. If the download is interrupted, run the installer again to resume.

## Talk
```bash
~/sophon-mac/sophon              # Chinese
~/sophon-mac/sophon --lang en    # English
```
Options: `--no-aec` turns echo cancellation off (headset), `--in` / `--out` pick audio devices (`--list` shows them), `--voice` picks a voice.
The first start loads the model in about 10 seconds.

## Speed (M4 Max, 36 GB)
| | |
|---|---|
| You stop talking → it starts speaking | **0.9–1.1 s** when the model is sure you have finished; up to about 2.5 s when it waits to see whether you continue |
| Long replies | real time, no stalls |
| You interrupt | it stops within about 0.15 s |

The server version answers in about 0.5 s. On a Mac, the turn decision (the model listens to your whole utterance) is computed on the Mac's GPU,
which is what takes most of the time; chips with more GPU cores (Max / Ultra) are faster.

## How it works
- The user's audio goes straight into the model through its own audio tower. When you pause, the model is asked in the same context whether you
  have finished; if yes, the reply continues from the same computation, so the audio is processed only once.
- Turn checks run at the server's schedule and thresholds (0.2 to 2 s of silence, then a fallback reply).
- Interrupting stops the reply at once and keeps only what was actually said in the conversation history. A short back-channel ("mm-hmm", "yeah")
  right after an interruption makes it resume where it was cut.
- Echo cancellation (WebRTC AEC3) removes the reply's own sound from the microphone, so it does not interrupt itself on speakers.

## Status and limits
- Tested on an M4 Max (36 GB) with real-time simulated audio input (speech played into the engine at real-time pace, simulated room echo).
  Live microphone runs and numbers from other Macs are very welcome in [issue #1](https://github.com/adventists-ai/sophon-realtime/issues/1).
- One conversation at a time. Camera input, tool calls and zero-shot voice cloning are not in the Mac version yet (built-in voices only).
