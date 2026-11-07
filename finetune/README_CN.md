# 用 ms-swift 微调 Sophon-Realtime v1

[English](README.md)

Sophon-Realtime v1 可以按业务场景微调**思考器**，也就是听用户说话、写回复的那部分。微调方式是在它的 LLM 主干上训练 LoRA。听觉编码器、投影器、说话头和发声部分都保持原样不动。

- **会变的**：回复的内容、人设、口吻、领域知识、工具调用习惯。
- **不变的**：
  - 接话判断：话轮题走不带 LoRA 的底座，微调影响不到。
  - 声音、音色和说话方式：它们由说话头决定。
- **笑声、咳嗽等声音表现会保留**：思考器在回复里写声音标签（`[laughter]`、`[cough]`、`<strong>…</strong>` 等），说话头照着标签演出来。所以微调要**从自带的写标签 LoRA 接着训**，不要从零训一个新 LoRA，否则模型就不会再写标签。

## 1. 环境

```bash
pip install "ms-swift>=4.6" "peft>=0.20,<0.21" "transformers>=4.51,<5.20" librosa soundfile
git clone https://github.com/adventists-ai/sophon-realtime
cd sophon-realtime/finetune          # 本目录，下面的命令都在这里执行
```

已验证：ms-swift 4.6.0、transformers 5.17.0、peft 0.20.0、torch 2.14（H100）。

## 2. 下载模型

微调只需要底座和写标签 LoRA：

```bash
modelscope download --model AdventistsAI/Sophon-Realtime-v1 --include 'base/*' 'adapters/*' --local_dir Sophon-Realtime-v1
python -m sophon_swift.adapters to-swift Sophon-Realtime-v1/adapters/tag tag_swift
```

第二条命令把写标签 LoRA 转成 ms-swift 可以接着训的格式。张量本身不变，只是把 LoRA 的作用范围限制在 LLM 上。

## 3. 数据格式

使用 ms-swift 标准的 jsonl 格式，每行一条对话。用户语音写成 `<audio>`，对应的文件按出现顺序列在 `audios` 里（16 kHz 单声道最好，其他采样率会自动重采样）。

```json
{"messages": [
  {"role": "system", "content": "你是「小航」，某航空公司的语音客服。……需要时可以用声音标签表现笑声、咳嗽和重读。"},
  {"role": "user", "content": "<audio>"},
  {"role": "assistant", "content": "[laughter]别担心，改签不收费的。您把航班号告诉我就行。"}
], "audios": ["data/0001.wav"]}
```

注意：

- **系统提示词末尾保留这一句**：「需要时可以用声音标签表现笑声、咳嗽和重读。」英文是 "When it fits, you may use sound tags for laughter, coughs and emphasis."。写标签 LoRA 就是在带这句的提示词下训出来的，去掉它，模型会少写标签。部署时用的提示词要和训练时一致。
- **回复写成"要说出口的话"**：口语、一两句话；不要用括号说明、表情或 markdown；数字、日期写成念法。在合适的地方可以自然地加 `[laughter]`、`[cough]`、`[sigh]`、`[breath]`、`<strong>重读的词</strong>`。
- **多轮**：历史轮次照常写，用户每一轮都可以是 `<audio>`。助手历史可以写文字；也可以放它当时说出的语音（`<audio>`），这部分只作为上下文，不参与训练。
- **工具调用**：与 Qwen 的格式相同。在 `tools` 字段放函数定义，助手回复里用 `<tool_call>{...}</tool_call>`，工具结果用 `role: tool`。

示例见 [examples/data_example.jsonl](examples/data_example.jsonl)（音频路径换成你自己的文件）。

**保留声音标签：混入回放数据。** 如果你自己的回复里很少带标签，微调后模型写标签也会变少。可以混入我们的[写标签回放数据](https://www.modelscope.cn/datasets/AdventistsAI/Sophon-Realtime-tag-replay)（8,797 条合成对话，约三分之一带标签）一起训：

```bash
modelscope download --dataset AdventistsAI/Sophon-Realtime-tag-replay --local_dir tag_replay
# 和你的数据一起放进 --dataset，数量取你数据的 20%–30% 左右，例如：
#   --dataset my_data.jsonl 'tag_replay/train.jsonl#2000'
```

其中的 `eval.jsonl`（150 条留出对话）可以直接用来做下面的回归检查。

## 4. 训练

一张 80 GB 显卡即可：

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

- `--adapters tag_swift` 表示从写标签 LoRA 接着训。LoRA 的秩固定是 16（alpha 32），与自带的那一个相同。
- `--freeze_vit / --freeze_aligner` 保持听觉编码器和投影器冻结。
- 显存实测（H100，样本长 2048 以内，batch 1）：单卡峰值约 65 GB；两张卡时 ms-swift 自动把模型切到两张卡上，每张约 34 GB。
- 学习率 5e-5 是起点。数据少（几百条）时用 2e-5–5e-5、1–2 个 epoch；数据多可以适当调高。

快速看效果：

```bash
CUDA_VISIBLE_DEVICES=0 swift infer \
  --custom_register_path sophon_swift/swift_register.py \
  --adapters output/vx-xxx/checkpoint-yyy \
  --val_dataset my_eval.jsonl --temperature 0 --max_new_tokens 128
```

## 5. 导出和部署

```bash
python -m sophon_swift.adapters to-vllm output/vx-xxx/checkpoint-yyy my_lora
```

部署时，用 `my_lora` **替换** `Sophon-Realtime-v1/adapters/tag`（或在部署配置里把写回复用的 LoRA 指向它），其余部署步骤不变。

- **不要合并 LoRA**（不要用 `swift export --merge_lora`）。思考器和说话头共用同一份底座，合并会改动说话头的输入，也会多占一份 32B 显存。
- 服务一次只挂一个回复 LoRA。你的 LoRA 是在写标签 LoRA 的基础上训出来的，已经包含了写标签的能力。

## 6. 回归检查

用 vLLM 同时挂上原来的 LoRA 和你的 LoRA，在一批留出的语音上对比两者的回复：

```bash
vllm serve Sophon-Realtime-v1/base --served-model-name base --port 8000 --max-model-len 8192 \
  --enable-lora --max-lora-rank 16 --max-loras 2 \
  --lora-modules tag=Sophon-Realtime-v1/adapters/tag mine=my_lora
python tools/regress.py --url http://127.0.0.1:8000 --data my_eval.jsonl --base tag --new mine
```

（vLLM 需要先 `pip install duplexjev-vllm` 才能加载这个结构。）

报告对比以下几项：

- 写标签的比例
- 不合法标签的数量
- 回复语言不对的数量
- 回复长度
- 两者逐字相同的条数

重点看两点：写标签的比例不要掉得太多；不合法标签和语言不对的数量应接近 0。

## 常见问题

- **能不能训听觉部分？** 这个版本不支持。听觉编码器和投影器决定了说话头读到的表示，改了它们，说话头就对不上了。
- **能不能换音色、训说话头？** 这次开源的微调只覆盖思考器。
- **报错 "audio tokens in prompt != audio embeddings"**：`<audio>` 的个数和 `audios` 里的文件数不一致。
