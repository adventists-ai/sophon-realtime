"""Qwen3-TTS talker (vLLM-Omni implementation) + streaming text input.
Text is not given all at once: each token the thinker writes is sent over (cumulative list ids.output); newly arrived tokens are projected and appended to the tail of trailing_text,
and a tts_eos is appended once the thinker finishes -- after that the original frame-by-frame text-reading decode logic is reused as-is (official streaming layout: the prefix contains only the first text token).
Voices: voices/<name>.pt (x-vector computed by the Base model's speaker encoder), looked up in the order "<voice>_<lang>" -> "<voice>"."""
import os
from typing import Any

import torch
from vllm.logger import init_logger
from vllm_omni.model_executor.models.qwen3_tts.qwen3_tts_talker import Qwen3TTSTalkerForConditionalGeneration

logger = init_logger("vllm_omni.sophon_realtime.talker")
LANG = {"zh": "chinese", "en": "english", "ja": "japanese", "ko": "korean", "de": "german", "fr": "french", "es": "spanish",
        "it": "italian", "pt": "portuguese", "ru": "russian"}
ROLE = [151644, 77091, 198]          # "<|im_start|>assistant\n"
PROMPT_LEN = 10                      # 3 role + 6 codec prefix + 1 (first text token)
FRAMES_PER_TOK = int(os.environ.get("SOPHON_FRAMES_PER_TOKEN", "12"))  # runaway guard: total frame cap ~= 12 frames/text token + 60


def _first(x, default=None):
    if isinstance(x, (list, tuple)):
        return x[0] if x else default
    return default if x is None else x


def _scalar_true(x) -> bool:
    if isinstance(x, torch.Tensor):
        return bool(x.reshape(-1)[0].item()) if x.numel() else False
    if isinstance(x, (list, tuple)):
        return bool(x and _scalar_true(x[0]))
    return bool(x)


class SophonTTSTalker(Qwen3TTSTalkerForConditionalGeneration):
    def __init__(self, *, vllm_config, prefix: str = ""):
        super().__init__(vllm_config=vllm_config, prefix=prefix)
        root = os.path.dirname(os.path.abspath(str(self.model_path).rstrip("/")))
        self._voice_dir = os.environ.get("SOPHON_VOICES") or os.path.join(root, "voices")
        self._voices: dict[str, torch.Tensor] = {}
        self._force_eos: set[str] = set()
        logger.info("SophonTTSTalker voices dir: %s (%s)", self._voice_dir,
                    sorted(os.listdir(self._voice_dir)) if os.path.isdir(self._voice_dir) else "missing")

    # ---------- helpers ----------
    def _te(self, ids, device) -> torch.Tensor:
        t = torch.tensor([list(ids)], dtype=torch.long, device=device)
        return self.text_projection(self.text_embedding(t)).reshape(len(ids), -1).to(self._embedding_dtype)

    def _ce(self, ids, device) -> torch.Tensor:
        t = torch.tensor(list(ids), dtype=torch.long, device=device).reshape(-1, 1)
        return self.embed_input_ids(t).reshape(len(ids), -1).to(self._embedding_dtype)

    def _voice(self, voice: str, lang: str, device) -> torch.Tensor:
        voice = (voice or "chelsie").lower().strip()
        for name in (f"{voice}_{lang}", voice, f"chelsie_{lang}", "chelsie_zh"):
            if name in self._voices:
                return self._voices[name].to(device)
            p = os.path.join(self._voice_dir, f"{name}.pt")
            if os.path.exists(p):
                self._voices[name] = torch.load(p, map_location="cpu").reshape(1, -1).to(self._embedding_dtype)
                return self._voices[name].to(device)
        raise ValueError(f"sophon_realtime: voice {voice!r} not found in {self._voice_dir}")

    @staticmethod
    def _ids(info) -> list[int]:
        ids = (info.get("ids") or {}).get("output") if isinstance(info.get("ids"), dict) else None
        if isinstance(ids, torch.Tensor):
            ids = ids.reshape(-1).tolist()
        return [int(x) for x in (ids or [])]

    @staticmethod
    def _fin(info) -> bool:
        meta = info.get("meta") or {}
        return _scalar_true(meta.get("finished", False))

    # ---------- batched prompt builder: not needed (the prefix is built in preprocess) ----------
    def preprocess_batch(self, **_: Any) -> None:
        return None

    def preprocess_batch_mrv2(self, **_: Any) -> None:
        return None

    # ---------- prefill ----------
    def _prefill(self, input_ids: torch.Tensor, info: dict) -> tuple[torch.Tensor, torch.Tensor, dict]:
        dev = input_ids.device; span = int(input_ids.shape[0])
        cfg = self.config; tc = self.talker_config
        ids = self._ids(info); fin = self._fin(info)
        lang = str(_first(info.get("language"), "zh") or "zh").lower()[:2]
        voice = str(_first(info.get("speaker"), "chelsie") or "chelsie")
        lang_id = tc.codec_language_id.get(LANG.get(lang, "english"), tc.codec_language_id["english"])
        bos, eos, pad = self._te([cfg.tts_bos_token_id, cfg.tts_eos_token_id, cfg.tts_pad_token_id], dev).split(1, 0)
        codec = torch.cat([self._ce([tc.codec_think_id, tc.codec_think_bos_id, lang_id, tc.codec_think_eos_id], dev),
                           self._voice(voice, lang, dev), self._ce([tc.codec_pad_id, tc.codec_bos_id], dev)], 0)     # (7, H)
        first = self._te(ids[:1], dev) if ids else pad
        pre = torch.cat([self._te(ROLE, dev), torch.cat([pad.expand(codec.shape[0] - 2, -1), bos], 0) + codec[:-1], first + codec[-1:]], 0)
        tail = [self._te(ids[1:], dev)] if len(ids) > 1 else []
        if fin:
            tail.append(eos)
        trailing = torch.cat(tail, 0) if tail else pre.new_zeros((0, pre.shape[1]))
        if pre.shape[0] != span:
            logger.warning_once("sophon talker prefill span %d != prompt %d; set hf_overrides.async_chunk_prewarm_prompt_len=%d",
                                span, pre.shape[0], PROMPT_LEN)
            pre = torch.cat([pre, pad.expand(max(0, span - pre.shape[0]), -1)], 0)[:span]
        ids_out = input_ids.clone(); ids_out[:] = int(tc.codec_pad_id)
        rid = info.get("request_id")
        if rid is not None:
            if fin and not ids:
                self._force_eos.add(rid)                  # no text (full-duplex turn-check request): finish immediately
            else:
                self._req_x_vector_only[rid] = True       # forbid silence in the first frames (original guard for x-vector cloning)
        upd = {
            "hidden_states": {"trailing_text": trailing.detach()},
            "meta": {"talker_text_offset": 0, "codec_streaming": True, "talker_prefill_offset": span,
                     "codec_frame_valid": torch.zeros((), dtype=torch.bool, device=dev),
                     "sophon_n": len(ids), "sophon_eos": fin},
            "codes": {"audio": torch.zeros((span, int(tc.num_code_groups)), dtype=torch.long, device=dev)},
        }
        return ids_out, pre, upd

    # ---------- decode: append newly arrived text to the tail of trailing_text ----------
    def _extend(self, info: dict, device) -> dict | None:
        meta = info.get("meta")
        if not isinstance(meta, dict):
            meta = {}; info["meta"] = meta
        ids = self._ids(info); fin = self._fin(info)
        n = int(meta.get("sophon_n", 0) or 0); eos_done = bool(meta.get("sophon_eos", False))
        steps = int(meta.get("sophon_steps", 0) or 0) + 1; post = int(meta.get("sophon_post", 0) or 0) + (1 if eos_done else 0)
        meta["sophon_steps"] = steps; meta["sophon_post"] = post
        rid = info.get("request_id")
        if rid is not None and eos_done and steps > FRAMES_PER_TOK * max(1, len(ids)) + 60:
            if rid not in self._force_eos:
                logger.warning("sophon talker: force codec EOS for %s (steps=%d post_eos=%d text_tokens=%d)", rid, steps, post, len(ids))
            self._force_eos.add(rid)
        add = []
        if len(ids) > n:
            add.append(self._te(ids[n:], device)); n = len(ids)
        if fin and not eos_done:
            add.append(self._te([self.config.tts_eos_token_id], device)); eos_done = True
        if not add:
            return {"sophon_steps": steps, "sophon_post": post}
        hs = info.get("hidden_states")
        if not isinstance(hs, dict):
            hs = {}; info["hidden_states"] = hs
        tail = hs.get("trailing_text"); off = int(meta.get("talker_text_offset", 0) or 0)
        rest = tail[off:].to(device=device, dtype=self._embedding_dtype) if isinstance(tail, torch.Tensor) and tail.ndim == 2 else None
        new_tail = torch.cat(([rest] if rest is not None and rest.shape[0] else []) + add, 0)
        hs["trailing_text"] = new_tail; meta["talker_text_offset"] = 0; meta["sophon_n"] = n; meta["sophon_eos"] = eos_done
        return {"trailing_text": new_tail, "sophon_n": n, "sophon_eos": eos_done, "sophon_steps": steps, "sophon_post": post}

    @staticmethod
    def _merge(upd: dict, ext: dict | None) -> dict:
        if ext is None:
            return upd
        upd.setdefault("meta", {}).update({k: v for k, v in ext.items() if k != "trailing_text"})
        if "trailing_text" in ext:
            hs = upd.setdefault("hidden_states", {})
            if "trailing_text" not in hs:
                hs["trailing_text"] = ext["trailing_text"].detach()
        return upd

    # ---------- runaway guard: force codec EOS when the cap is reached ----------
    def set_batch_req_ids(self, req_ids) -> None:
        super().set_batch_req_ids(req_ids)
        if self._force_eos:
            live = set(self._batch_req_ids)
            self._force_eos &= live

    def compute_logits(self, hidden_states, sampling_metadata: Any = None):
        logits = super().compute_logits(hidden_states, sampling_metadata)
        if logits is None or not self._force_eos:
            return logits
        rows = [i for i, r in enumerate(self._batch_req_ids) if r in self._force_eos] if len(self._batch_req_ids) == logits.shape[0] else []
        if rows:
            idx = torch.tensor(rows, device=logits.device)
            logits[idx] = logits[idx] - 1e4; logits[idx, self._codec_eos_token_id] = 0.0   # not -inf: avoids an all -inf row when min_tokens masks EOS
        return logits

    def preprocess(self, input_ids: torch.Tensor, input_embeds: torch.Tensor | None, **info_dict: Any):
        add = info_dict.get("additional_information")
        if isinstance(add, dict):
            merged = {k: v for k, v in info_dict.items() if k != "additional_information"}
            for k, v in add.items():
                merged.setdefault(k, v)
            info_dict = merged
        span = int(input_ids.shape[0])
        is_prefill = info_dict.get("_omni_is_prefill")
        if not isinstance(is_prefill, bool):
            is_prefill = span > 1
        if is_prefill and span > 0:
            return self._prefill(input_ids, info_dict)
        ext = self._extend(info_dict, input_ids.device)
        ids_o, emb_o, upd = super().preprocess(input_ids, input_embeds, **info_dict)
        return ids_o, emb_o, self._merge(upd, ext)

    def preprocess_decode_batch(self, *, input_ids: torch.Tensor, req_infos: list[dict[str, Any]], input_embeds: torch.Tensor | None = None):
        exts = [self._extend(info, input_ids.device) for info in req_infos]
        out = super().preprocess_decode_batch(input_ids=input_ids, req_infos=req_infos, input_embeds=input_embeds)
        updates = out[-1]
        for i, ext in enumerate(exts):
            updates[i] = self._merge(updates[i], ext)
        return out
