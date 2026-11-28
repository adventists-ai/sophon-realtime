# Copyright 2026 Adventists AI. Apache-2.0.
"""Merge a thinker LoRA into a base thinker, on CPU, in the file layout of a released thinker/ folder.

The 4B builds (Sophon-Realtime-4B-Tag / -Flash / -E2E) ship the thinker with the tag LoRA already merged, and their
servers do not attach a LoRA at run time. After fine-tuning the 4B tag LoRA, merge it into the plain base
(DuplexJev-4B-Para) and use the result as the build's thinker/:

    python -m sophon_swift.merge --base DuplexJev-4B-Para --lora output/vx-xxx/checkpoint-yyy \
        --like Sophon-Realtime-4B-Flash/thinker --out thinker_mine

--like gives everything except the weights (config, tokenizer, chat template) and the shard layout. Only the LLM
layers are changed; the audio encoder and the projector are copied from --base unchanged. No GPU needed (~17 GB RAM).
"""
import argparse
import json
import os
import shutil
from collections import defaultdict

PREFIX = "base_model.model."


def load_lora(path):
    from safetensors.torch import load_file
    cfg = json.load(open(os.path.join(path, "adapter_config.json")))
    if cfg.get("modules_to_save"):
        raise ValueError("modules_to_save is not supported; train LoRA on the LLM only")
    scale = cfg["lora_alpha"] / cfg["r"]
    if cfg.get("use_rslora"):
        scale = cfg["lora_alpha"] / cfg["r"] ** 0.5
    t = load_file(os.path.join(path, "adapter_model.safetensors"))
    pairs = {}
    for k in t:
        if k.endswith(".lora_A.weight"):
            name = k[len(PREFIX):-len(".lora_A.weight")] + ".weight"
            pairs[name] = (t[k], t[k.replace(".lora_A.", ".lora_B.")])
    if len(pairs) * 2 != len(t):
        raise ValueError(f"unexpected tensors in {path}: {len(t)} tensors, {len(pairs)} LoRA pairs")
    return pairs, scale


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--base", required=True, help="plain base thinker, e.g. DuplexJev-4B-Para")
    ap.add_argument("--lora", required=True, help="ms-swift checkpoint or vLLM adapter folder")
    ap.add_argument("--like", required=True, help="a released thinker/ folder (gives config, tokenizer, shard layout)")
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    import torch
    from safetensors import safe_open
    from safetensors.torch import save_file

    pairs, scale = load_lora(a.lora)
    like_map = json.load(open(os.path.join(a.like, "model.safetensors.index.json")))["weight_map"]
    base_map = json.load(open(os.path.join(a.base, "model.safetensors.index.json")))["weight_map"]
    if set(like_map) != set(base_map):
        raise ValueError("--base and --like hold different tensors; are they the same model size?")
    missing = [k for k in pairs if k not in base_map]
    if missing:
        raise ValueError(f"{len(missing)} LoRA targets not in the base (e.g. {missing[0]}); wrong base model?")

    os.makedirs(a.out, exist_ok=True)
    for f in os.listdir(a.like):
        p = os.path.join(a.like, f)
        if os.path.isfile(p) and not f.endswith(".safetensors") and f != "model.safetensors.index.json":
            shutil.copy2(p, os.path.join(a.out, f))

    by_shard = defaultdict(list)
    for k, shard in like_map.items():
        by_shard[shard].append(k)
    handles = {}
    total, merged = 0, 0
    for shard in sorted(by_shard):
        out = {}
        for k in by_shard[shard]:
            src = base_map[k]
            if src not in handles:
                handles[src] = safe_open(os.path.join(a.base, src), "pt")
            w = handles[src].get_tensor(k)
            if k in pairs:
                A, B = pairs[k]
                w = (w.float() + scale * (B.float() @ A.float())).to(w.dtype)
                merged += 1
            out[k] = w.contiguous()
            total += w.numel() * w.element_size()
        save_file(out, os.path.join(a.out, shard), metadata={"format": "pt"})
        print(f"wrote {shard} ({len(out)} tensors)", flush=True)
    json.dump({"metadata": {"total_size": total}, "weight_map": like_map},
              open(os.path.join(a.out, "model.safetensors.index.json"), "w"), indent=2)
    print(f"merged {merged} LoRA pairs (scale {scale:g}) into {a.out}")


if __name__ == "__main__":
    main()
