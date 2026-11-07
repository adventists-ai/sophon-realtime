# Copyright 2026 Adventists AI. Apache-2.0.
"""Where the released files live. Set SOPHON_MODEL_DIR to the downloaded Sophon-Realtime-v1 directory."""
import os


def model_dir() -> str:
    d = os.environ.get("SOPHON_MODEL_DIR", "")
    if not d or not os.path.isdir(d):
        raise RuntimeError("Set SOPHON_MODEL_DIR to the Sophon-Realtime-v1 model directory "
                           "(modelscope download --model AdventistsAI/Sophon-Realtime-v1 --local_dir ...)")
    return os.path.abspath(d)


def base_dir() -> str:
    return os.path.join(model_dir(), "base")


def tag_adapter_dir() -> str:
    return os.environ.get("SOPHON_REPLY_LORA") or os.path.join(model_dir(), "adapters", "tag")


def talker_weights() -> str:
    return os.path.join(model_dir(), "talker", "model.safetensors")


def e2_dir() -> str:
    return os.path.join(model_dir(), "e2")


def voice_file(name: str = "chelsie") -> str:
    return os.path.join(model_dir(), "voices", f"{name}.safetensors")
