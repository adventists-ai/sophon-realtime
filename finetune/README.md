# Fine-tuning Sophon-Realtime v1 with ms-swift

[中文](README_CN.md)

You can adapt the **thinker** of Sophon-Realtime v1 (the part that listens and writes the reply) to your use case by training a LoRA on its LLM backbone. The audio encoder, the projector, the talker and the vocoder stay as released.

- **What changes:** what the model says — content, persona, tone, domain knowledge, tool-calling habits.
- **What does not:** turn-taking (turn questions go to the base model without the LoRA), and the voice, timbre and delivery (the talker).
- **Expressive speech is kept:** the thinker writes sound tags (`[laughter]`, `[cough]`, `<strong>…</strong>`, …) and the talker performs them. Fine-tuning therefore **continues the bundled tag LoRA** instead of starting a new one; otherwise the model stops writing tags.

## 1. Install

```bash
pip install "ms-swift>=4.6" "peft>=0.20,<0.21" "transformers>=4.51,<5.20" librosa soundfile
git clone https://github.com/adventists-ai/sophon-realtime
cd sophon-realtime/finetune          # run everything below from here
```

Tested with ms-swift 4.6.0, transformers 5.17.0, peft 0.20.0, torch 2.14 on H100.

## 2. Download

Fine-tuning needs only the base weights and the tag LoRA:

```bash
modelscope download --model AdventistsAI/Sophon-Realtime-v1 --include 'base/*' 'adapters/*' --local_dir Sophon-Realtime-v1
python -m sophon_swift.adapters to-swift Sophon-Realtime-v1/adapters/tag tag_swift
```

The second command re-labels the tag LoRA so that ms-swift continues training it on the LLM only. The tensors are unchanged.

## 3. Data

Use the standard ms-swift jsonl format, one conversation per line. Write `<audio>` where the user speaks and list the files in `audios`, in order. 16 kHz mono is preferred; other sample rates are resampled.

```json
{"messages": [
  {"role": "system", "content": "You are Ava, the voice agent of a small airline. ... When it fits, you may use sound tags for laughter, coughs and emphasis."},
  {"role": "user", "content": "<audio>"},
  {"role": "assistant", "content": "Your flight leaves at <strong>seven</strong> forty, not seven fourteen, so you have plenty of time."}
], "audios": ["data/0002.wav"]}
```

- **End the system prompt with the sound-tag sentence:** "When it fits, you may use sound tags for laughter, coughs and emphasis." In Chinese: 「需要时可以用声音标签表现笑声、咳嗽和重读。」 The tag LoRA was trained with it, and without it the model writes fewer tags. Serve with the same prompt you train with.
- **Write replies as speech:** one or two conversational sentences; no stage directions, emoji or markdown; numbers written the way they are read. Add `[laughter]`, `[cough]`, `[sigh]`, `[breath]` or `<strong>word</strong>` where they fit naturally.
- **Multi-turn:** every user turn can be `<audio>`. Assistant history can be text, or the audio it actually spoke (`<audio>`). Assistant audio is context only and is never trained on.
- **Tools:** use the Qwen format. Put the function schemas in `tools`, write calls as `<tool_call>{...}</tool_call>` in the assistant reply, and return results with `role: tool`.

See [examples/data_example.jsonl](examples/data_example.jsonl) (replace the audio paths with your own files).

## 4. Train

One 80 GB GPU is enough:

```bash
CUDA_VISIBLE_DEVICES=0 swift sft \
  --custom_register_path sophon_swift/swift_register.py \
  --model Sophon-Realtime-v1 \
  --adapters tag_swift \
  --tuner_type lora \
  --torch_dtype bfloat16 \
  --dataset my_data.jsonl \
  --max_length 4096 \
  --num_train_epochs 2 \
  --learning_rate 5e-5 \
  --per_device_train_batch_size 1 \
  --gradient_accumulation_steps 8 \
  --gradient_checkpointing true \
  --freeze_vit true --freeze_aligner true \
  --save_steps 100 --logging_steps 5 \
  --output_dir output
```

- `--adapters tag_swift` continues the tag LoRA. Its rank is fixed at 16 (alpha 32).
- Measured on H100, with samples up to 2048 tokens and batch size 1: about 65 GB peak on one GPU. With two GPUs, ms-swift splits the model and uses about 34 GB on each.
- 5e-5 is a starting point. For a few hundred samples, use 2e-5 to 5e-5 for 1–2 epochs.

Quick look:

```bash
CUDA_VISIBLE_DEVICES=0 swift infer \
  --custom_register_path sophon_swift/swift_register.py \
  --adapters output/vx-xxx/checkpoint-yyy \
  --val_dataset my_eval.jsonl --temperature 0 --max_new_tokens 128
```

## 5. Export and serve

```bash
python -m sophon_swift.adapters to-vllm output/vx-xxx/checkpoint-yyy my_lora
```

**Replace** `Sophon-Realtime-v1/adapters/tag` with `my_lora`, or point the reply LoRA in your deployment config to it. Deploy as usual.

- **Do not merge the LoRA** (no `swift export --merge_lora`). The thinker and the talker share one copy of the base weights. Merging would change what the talker reads and cost another 32B of memory.
- The server attaches one reply LoRA per request. Yours already includes the tag-writing behaviour, because it was trained on top of the tag LoRA.

## 6. Regression check

Serve both LoRAs side by side, then compare their replies on held-out audio:

```bash
pip install duplexjev-vllm   # lets vLLM load this architecture
vllm serve Sophon-Realtime-v1/base --served-model-name base --port 8000 --max-model-len 8192 \
  --enable-lora --max-lora-rank 16 --max-loras 2 \
  --lora-modules tag=Sophon-Realtime-v1/adapters/tag mine=my_lora
python tools/regress.py --url http://127.0.0.1:8000 --data my_eval.jsonl --base tag --new mine
```

The report compares:

- sound-tag rate
- malformed tags
- replies in the wrong language
- reply length
- how many replies are identical

Keep the tag rate close to the original, and keep malformed tags and wrong-language replies near zero.

## FAQ

- **Can I train the audio side?** Not in this release. The talker reads the audio representation, so changing the encoder or the projector would break it.
- **Can I change the voice or train the talker?** Fine-tuning in this release covers the thinker only.
- **"audio tokens in prompt != audio embeddings":** the number of `<audio>` tags does not match the number of files in `audios`.
