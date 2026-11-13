"""One-time conversion of the Sophon-Realtime-32B-Flash-4bit download into the Mac (MLX) layout. Lossless: the 4-bit weights are repacked,
not requantized (compressed-tensors int4 group-128 nibbles are bit-identical to MLX's 4-bit layout).

    python convert.py SRC_DIR DST_DIR [--delete-src]

SRC_DIR = the downloaded repo (thinker/, talker/, voices/).  DST_DIR gets: thinker_mlx/ (the 4-bit thinker for mlx_lm), ear/ (audio tower +
projector + feature-extractor config), talker/ (moved or linked), voices/*.npy."""
import argparse, glob, io, json, os, pickle, shutil, sys, zipfile
import numpy as np, mlx.core as mx

ap = argparse.ArgumentParser(); ap.add_argument("src"); ap.add_argument("dst"); ap.add_argument("--delete-src", action="store_true")
a = ap.parse_args(); SRC = os.path.join(a.src, "thinker"); DST = a.dst; os.makedirs(DST, exist_ok=True)

# 1) thinker -> an mlx_lm text model (4-bit, same weights)
T = os.path.join(DST, "thinker_mlx"); os.makedirs(T, exist_ok=True)
c = json.load(open(f"{SRC}/config.json")); t = c["text_config"]
cfg = {"model_type": "qwen3", "architectures": ["Qwen3ForCausalLM"], "hidden_size": t["hidden_size"], "num_hidden_layers": t["num_hidden_layers"],
       "intermediate_size": t["intermediate_size"], "num_attention_heads": t["num_attention_heads"], "num_key_value_heads": t["num_key_value_heads"],
       "head_dim": t["head_dim"], "rms_norm_eps": t["rms_norm_eps"], "vocab_size": t["vocab_size"], "rope_theta": t["rope_parameters"]["rope_theta"],
       "tie_word_embeddings": False, "max_position_embeddings": 32768, "quantization": {"group_size": 128, "bits": 4}}
json.dump(cfg, open(f"{T}/config.json", "w"), indent=1)
for f in ["tokenizer.json", "tokenizer_config.json", "vocab.json", "merges.txt", "special_tokens_map.json", "added_tokens.json", "chat_template.jinja",
          "generation_config.json"]:
    if os.path.exists(f"{SRC}/{f}"): shutil.copy(f"{SRC}/{f}", T)
wmap = {}; n = 0; proj = {}
shards = sorted(glob.glob(f"{SRC}/model-w4-*.safetensors"))
for i, sf in enumerate(shards):
    W = mx.load(sf); out = {}
    for k, v in W.items():
        if k.startswith("multi_modal_projector."): proj[k] = v; continue
        if not k.startswith("language_model."): continue
        k = k[len("language_model."):]
        if k.endswith(".weight_packed"): out[k[:-len(".weight_packed")] + ".weight"] = v.view(mx.uint32)
        elif k.endswith(".weight_scale"):
            b = k[:-len(".weight_scale")]; out[b + ".scales"] = v; out[b + ".biases"] = (v * -8).astype(v.dtype)
        elif k.endswith(".weight_shape"): continue
        else: out[k] = v
    if out:
        name = f"model-{n:05d}.safetensors"; mx.save_safetensors(f"{T}/{name}", out); n += 1
        for k in out: wmap[k] = name
    print(f"thinker {i + 1}/{len(shards)}", flush=True); del W, out
json.dump({"metadata": {}, "weight_map": wmap}, open(f"{T}/model.safetensors.index.json", "w"))

# 2) ear = audio tower + projector (the projector lives in the main shards; the copy under thinker/audio/ is stale and is NOT used)
E = os.path.join(DST, "ear"); os.makedirs(E, exist_ok=True)
W = {k: v for k, v in mx.load(f"{SRC}/audio/model.safetensors").items() if k.startswith("audio_tower.")}
W.update(proj); mx.save_safetensors(f"{E}/ear.safetensors", W)
ac = json.load(open(f"{SRC}/audio/config.json")); json.dump(ac, open(f"{E}/config.json", "w"), indent=1)
for f in glob.glob(f"{SRC}/audio/*.json"):
    if os.path.basename(f) != "config.json": shutil.copy(f, E)
print("ear", len(W), "tensors", flush=True)

# 3) talker
dt = os.path.join(DST, "talker")
if not os.path.exists(dt):
    if a.delete_src: shutil.move(os.path.join(a.src, "talker"), dt)
    else: os.symlink(os.path.abspath(os.path.join(a.src, "talker")), dt)

# 4) voices: torch .pt (one tensor) -> .npy, read without torch
def load_pt(path):
    z = zipfile.ZipFile(path); names = z.namelist(); root = names[0].split("/")[0]
    DT = {"FloatStorage": np.float32, "BFloat16Storage": "bf16", "HalfStorage": np.float16, "DoubleStorage": np.float64}
    class U(pickle.Unpickler):
        def find_class(self, mod, name):
            if mod == "torch._utils" and name == "_rebuild_tensor_v2":
                def rebuild(st, off, size, stride, *rest):
                    raw, kind = st
                    arr = (np.frombuffer(raw, np.uint16).astype(np.uint32) << 16).view(np.float32) if kind == "bf16" else np.frombuffer(raw, kind)
                    return np.lib.stride_tricks.as_strided(arr[off:], size, [s * arr.itemsize for s in stride]).copy()
                return rebuild
            if mod == "torch": return name
            if mod == "collections" and name == "OrderedDict":
                import collections; return collections.OrderedDict
            return super().find_class(mod, name)
        def persistent_load(self, pid):
            _, stype, key, _, _ = pid; return (z.read(f"{root}/data/{key}"), DT[stype])
    return U(io.BytesIO(z.read(f"{root}/data.pkl"))).load()
V = os.path.join(DST, "voices"); os.makedirs(V, exist_ok=True)
for p in glob.glob(os.path.join(a.src, "voices", "*.pt")):
    x = load_pt(p); x = np.asarray(x, np.float32); np.save(os.path.join(V, os.path.basename(p)[:-3] + ".npy"), x); print("voice", os.path.basename(p), x.shape)
if a.delete_src:
    shutil.rmtree(SRC); print("removed", SRC)
print("CONVERT_DONE", DST)
