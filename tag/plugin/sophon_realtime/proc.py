"""Step-by-step thinker -> tag-tts talker forwarding (Sophon-Realtime-32B-Tag).
Every thinker step sends the talker the *cumulative* CosyVoice token ids of the reply written so far:
- sound tags are kept whole and passed through (whitelist: [laughter] [breath] [sigh] [cough] [quick_breath],
  <laughter>..</laughter>, <strong>..</strong>); anything else in brackets and markdown symbols is dropped; an unclosed
  bracket at the end is held back; <strong> is auto-closed at punctuation; open spans are closed when the thinker finishes
  (same rules as the Tag one-box server sophon_tag_server.TagStream).
- the text is re-tokenized with the tag-tts (CosyVoice3) tokenizer, so every tag is one special token.
- the last token is held back until the next step (it may still merge); everything is released when the thinker finishes.
- a chunk is sent on *every* thinker step once LEAD tokens are ready (heartbeat): in async-chunk mode the talker only steps
  when a chunk arrives, and it needs ~4 steps per text token (bistream 5 text : 15 speech + the text positions)."""
import os
import re
import threading

import torch
from .tools import cut_tool
from vllm_omni.data_entry_keys import IdsStruct, MetaStruct, OmniPayloadStruct
from vllm_omni.model_executor.stage_input_processors.tts_utils import extract_language_from_request, extract_speaker_from_request

LEAD = int(os.environ.get("SOPHON_LEAD", "5"))
POINT = {"[laughter]", "[breath]", "[sigh]", "[cough]", "[quick_breath]"}
SPAN = {"laughter", "strong"}
CLOSE = {"[": "]", "<": ">", "(": ")", "（": "）", "【": "】"}
_TOK = None
_TTOK = None
_LOCK = threading.Lock()
_ST: dict[str, dict] = {}


def tag_clean(s: str, final: bool) -> str:
    """Whole-string version of sophon_tag_server.TagStream (returns the text with whitelisted tags kept)."""
    out: list[str] = []; open_: list[str] = []; buf = s

    def emit_tag(t):
        m = re.fullmatch(r"<(/?)([a-z_\-]+)>", t)
        if t in POINT:
            out.append(t); return
        if m and m.group(2) in SPAN:
            name = m.group(2)
            if not m.group(1):
                if name not in open_:
                    open_.append(name); out.append(t)
            elif name in open_:
                open_.remove(name); out.append(t)

    def text(v):
        v = v.replace("→", ", so ").replace("⇒", ", so ").replace("≥", " at least ").replace("≤", " at most ")
        if "strong" in open_:
            m = re.search(r"[，。！？、,.!?;；:：]", v)
            if m:
                if m.start(): out.append(v[:m.start()])
                out.append("</strong>"); open_.remove("strong"); v = v[m.start():]
        if v: out.append(v)

    while buf:
        idx = [k for k in (buf.find(c) for c in list(CLOSE) + ["*", "#", "`"]) if k >= 0]
        i = min(idx) if idx else -1
        if i < 0:
            text(buf); buf = ""; break
        if i > 0:
            text(buf[:i]); buf = buf[i:]
        c = buf[0]
        if c in "*#`":
            buf = buf[1:]; continue
        j = buf.find(CLOSE[c], 1)
        if j < 0:
            if len(buf) > 40:
                buf = buf[1:]; continue
            break
        tok, buf = buf[:j + 1], buf[j + 1:]
        if c in "[<":
            emit_tag(tok)
    if final:
        if buf:
            t = re.sub(r"[\[<(（【].*$", "", buf)
            if t: text(t)
        for name in reversed(open_): out.append(f"</{name}>")
    return "".join(out)


TAG_RE = re.compile(r"\[(?:laughter|breath|sigh|cough|quick_breath)\]|</?(?:laughter|strong)>")


def strip_tags(s: str) -> str:
    return TAG_RE.sub("", s)


def _tokenizer(tm):
    global _TOK
    if _TOK is None:
        with _LOCK:
            if _TOK is None:
                from transformers import AutoTokenizer
                path = os.environ.get("SOPHON_TOKENIZER")
                if not path:
                    from .env import model_dir
                    d = model_dir()
                    if d and os.path.isdir(os.path.join(d, "thinker")):
                        path = os.path.join(d, "thinker")
                if not path:
                    raise RuntimeError("sophon_realtime: cannot locate thinker tokenizer; set SOPHON_TOKENIZER")
                _TOK = AutoTokenizer.from_pretrained(path)
    return _TOK


def _talker_tokenizer():
    global _TTOK
    if _TTOK is None:
        with _LOCK:
            if _TTOK is None:
                from vllm_omni.model_executor.models.cosyvoice3.tokenizer import get_qwen_tokenizer
                from .env import model_dir
                path = os.environ.get("SOPHON_TALKER_TOKENIZER") or os.path.join(model_dir(), "talker", "CosyVoice-BlankEN")
                _TTOK = get_qwen_tokenizer(path, skip_special_tokens=True, version="cosyvoice3")
    return _TTOK


def _entry(request, key):
    info = getattr(request, "additional_information", None)
    entries = getattr(info, "entries", None)
    if not isinstance(entries, dict) or key not in entries:
        return None
    data = getattr(entries[key], "list_data", None)
    return data[0] if isinstance(data, list) and data else None


def thinker2talker_async_chunk(transfer_manager, multimodal_output, request, is_finished: bool = False):
    rid = request.external_req_id
    if _entry(request, "sophon_kind") == "check":       # full-duplex turn-check query: the talker gets no text
        if not is_finished:
            return None
        return OmniPayloadStruct(ids=IdsStruct(output=[]), meta=MetaStruct(finished=torch.tensor(True, dtype=torch.bool)))
    tok = _tokenizer(transfer_manager)
    out = [int(t) for t in (request.output_token_ids or [])]
    raw = cut_tool(tok.decode(out, skip_special_tokens=True), is_finished)
    text = tag_clean(raw, is_finished).lstrip()
    ids = _talker_tokenizer().encode(text, allowed_special="all") if text else []
    stable = ids if is_finished else ids[:-1]
    st = _ST.setdefault(rid, {"sent": 0})
    if not is_finished:
        if st["sent"] == 0 and len(stable) < LEAD:
            return None
    else:
        _ST.pop(rid, None)
    st["sent"] = max(st["sent"], len(stable), 1)
    return OmniPayloadStruct(
        ids=IdsStruct(output=list(stable)),
        meta=MetaStruct(finished=torch.tensor(bool(is_finished), dtype=torch.bool)),
        speaker=extract_speaker_from_request(request),
        language=extract_language_from_request(request),
    )


# ---------------------------------------------------------------- talker -> code2wav: add the voice prompt once
_VOICES: dict[str, dict] = {}


def _voice_payload(request):
    from vllm_omni.engine.serialization import deserialize_additional_information
    info = deserialize_additional_information(getattr(request, "additional_information", None))
    info = info if isinstance(info, dict) else {}
    def first(x):
        return x[0] if isinstance(x, (list, tuple)) and x else x
    name = str(first(info.get("speaker")) or "").lower().strip()
    lang = str(first(info.get("language")) or "zh").lower()[:2]
    from .env import model_dir
    vdir = os.environ.get("SOPHON_VOICES") or os.path.join(model_dir(), "voices")
    for n in (name, f"{name}_{lang}", f"chelsie_{lang}", "vivian_zh" if lang == "zh" else "ryan_en", "vivian_zh"):
        if not n:
            continue
        if n not in _VOICES and os.path.exists(os.path.join(vdir, f"{n}.pt")):
            _VOICES[n] = torch.load(os.path.join(vdir, f"{n}.pt"), map_location="cpu")
        if n in _VOICES:
            v = _VOICES[n]
            return {"embed": {"speech_token": v["speech_token"], "speech_feat": v["speech_feat"], "embedding": v["embedding"],
                              "speech_token_len": torch.tensor([[v["speech_token"].shape[1]]], dtype=torch.int32)}}
    raise ValueError(f"sophon tag: voice {name!r} not found in {vdir}")


def talker2code2wav_async_chunk(transfer_manager, multimodal_output, request, is_finished: bool = False):
    """vLLM-Omni's CosyVoice3 chunker, with the voice prompt (precomputed flow conditioning) supplied on the first call."""
    from vllm_omni.model_executor.stage_input_processors import cosyvoice3 as _cv
    state = transfer_manager.request_payload.get(request.external_req_id)
    if not isinstance(state, dict) or "_cosyvoice3_async_state" not in state:
        multimodal_output = _voice_payload(request)
    return _cv.talker2code2wav_async_chunk(transfer_manager, multimodal_output, request, is_finished)
