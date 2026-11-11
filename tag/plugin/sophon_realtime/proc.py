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
from vllm.logger import init_logger
from .tools import cut_tool
from vllm_omni.data_entry_keys import IdsStruct, MetaStruct, OmniPayloadStruct
from vllm_omni.model_executor.stage_input_processors.tts_utils import extract_language_from_request, extract_speaker_from_request

logger = init_logger("vllm_omni.sophon_realtime.proc")

LEAD = int(os.environ.get("SOPHON_LEAD", "5"))
# One reply speaks at most about REPLY_S seconds and always stops at a sentence end. The cut is a pure function of the
# thinker text (budget_plan), so the talker (here) and the session (duplex.py) compute the same point: the spoken audio,
# the caption and the history all end at the same sentence, and the session can continue seamlessly from there.
REPLY_S = float(os.environ.get("SOPHON_MAX_REPLY_S", "45"))
HOLD_S = 8.0          # within this many seconds of the budget, only complete sentences go to the talker
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


def last_boundary(raw: str, limit: int | None = None) -> int:
    """Index just after the last sentence end in raw thinker text (outside [..] / <..> tags), at most `limit`; 0 if none."""
    best = 0; depth = None; n = len(raw) if limit is None else min(limit, len(raw))
    for i in range(n):
        c = raw[i]
        if depth:
            if c == depth: depth = None
            continue
        if c in "[<": depth = "]" if c == "[" else ">"; continue
        if c in "。！？!?；;\n" or (c == "." and i + 1 < len(raw) and raw[i + 1].isspace()):
            j = i + 1
            while j < len(raw) and raw[j] in "\"'”’)）」』": j += 1
            if j <= n: best = j
    return best


def speech_seconds(text: str) -> float:
    """Rough spoken length of cleaned text: CJK characters ~0.22 s, other words ~0.4 s."""
    t = strip_tags(text); cjk = sum(1 for c in t if "\u3040" <= c <= "\u9fff" or "\uac00" <= c <= "\ud7af")
    words = len(re.sub(r"[\u3040-\u9fff\uac00-\ud7af]", " ", t).split())
    return cjk * 0.22 + words * 0.4


def _soft_breaks(raw: str, n: int) -> int:
    """Index just after the last comma / colon / space before n (outside tags); 0 if none."""
    best = 0; depth = None
    for i in range(min(n, len(raw))):
        c = raw[i]
        if depth:
            if c == depth: depth = None
            continue
        if c in "[<": depth = "]" if c == "[" else ">"; continue
        if c in "，,、：:" or c.isspace(): best = i + 1
    return best


def _secs(raw: str) -> float:
    return speech_seconds(tag_clean(raw, True))


def _fit(raw: str, limit_s: float) -> int:
    """Largest index i such that raw[:i] takes at most limit_s seconds to say (spoken length only grows with i)."""
    lo, hi = 0, len(raw)
    while lo < hi:
        mid = (lo + hi + 1) // 2
        if _secs(raw[:mid]) <= limit_s: lo = mid
        else: hi = mid - 1
    return lo


def budget_plan(raw: str) -> tuple[int, bool] | None:
    """Speech budget for one reply, as a pure function of the raw thinker text (so the talker in proc.py and the
    session in duplex.py always agree). Returns None while the reply is short, else (limit, done):
    - limit: only raw[:limit] may be spoken / captioned for now;
    - done: the reply is over budget and ends exactly at raw[:limit].
    In the last HOLD_S seconds before the budget only whole sentences are released (but never less than the text that
    fits before that zone, z), and the final cut is the last sentence end in [z, budget], else the last comma / space in
    that range, else the last character that fits. Everything released earlier is therefore always inside the cut."""
    if REPLY_S <= 0:
        return None
    total = _secs(raw)
    if total <= REPLY_S - HOLD_S:
        return None
    z = _fit(raw, REPLY_S - HOLD_S)
    if total <= REPLY_S:
        return max(z, last_boundary(raw)), False
    e = _fit(raw, REPLY_S)
    b = last_boundary(raw, e)
    if b >= z and b > 0:
        return b, True
    s = _soft_breaks(raw, e)
    if s >= z and s > 0:
        return s, True
    return e, True


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
    st = _ST.setdefault(rid, {"sent": 0, "raw_len": 0})
    if st.get("closed"):
        if is_finished: _ST.pop(rid, None)
        return None
    final = is_finished; close = False
    plan = budget_plan(raw)
    if plan is not None:                       # speech budget (see budget_plan): never release text past the plan's limit
        limit, done = plan
        raw = raw[:max(limit, 0)]
        if done:
            final = True; close = not is_finished
    text = tag_clean(raw, final).lstrip()
    ids = _talker_tokenizer().encode(text, allowed_special="all") if text else []
    stable = ids if final else ids[:-1]
    if not final:
        if st["sent"] == 0 and len(stable) < LEAD:
            return None
        if len(stable) < st["sent"]:
            return None
    if is_finished:
        _ST.pop(rid, None)
    elif close:
        st["closed"] = True
    else:
        st["raw_len"] = max(st["raw_len"], len(raw))
    st["sent"] = max(st["sent"], len(stable), 1)
    is_finished = final
    return OmniPayloadStruct(
        ids=IdsStruct(output=list(stable)),
        meta=MetaStruct(finished=torch.tensor(bool(is_finished), dtype=torch.bool)),
        speaker=extract_speaker_from_request(request),
        language=extract_language_from_request(request),
    )


# ---------------------------------------------------------------- talker -> code2wav: add the voice prompt once


def _voice_payload(request):
    from vllm_omni.engine.serialization import deserialize_additional_information
    from . import voices
    from .env import model_dir
    info = deserialize_additional_information(getattr(request, "additional_information", None))
    info = info if isinstance(info, dict) else {}
    def first(x):
        return x[0] if isinstance(x, (list, tuple)) and x else x
    name = str(first(info.get("speaker")) or "")
    lang = str(first(info.get("language")) or "zh").lower()[:2]
    vdir = os.environ.get("SOPHON_VOICES") or os.path.join(model_dir(), "voices")
    got, v = voices.load(vdir, name, lang, os.path.join(model_dir(), "talker"), log=logger)
    if name and got not in (name.lower().strip(), f"{name.lower().strip()}_{lang}") and name.lower().strip() not in _MISSING:
        _MISSING.add(name.lower().strip())
        logger.warning("sophon tag: voice %r not found in %s, using %s", name, vdir, got)
    return {"embed": {"speech_token": v["speech_token"], "speech_feat": v["speech_feat"], "embedding": v["embedding"],
                      "speech_token_len": torch.tensor([[v["speech_token"].shape[1]]], dtype=torch.int32)}}


_MISSING: set[str] = set()


def talker2code2wav_async_chunk(transfer_manager, multimodal_output, request, is_finished: bool = False):
    """vLLM-Omni's CosyVoice3 chunker, with the voice prompt (precomputed flow conditioning) supplied on the first call."""
    from vllm_omni.model_executor.stage_input_processors import cosyvoice3 as _cv
    state = transfer_manager.request_payload.get(request.external_req_id)
    if not isinstance(state, dict) or "_cosyvoice3_async_state" not in state:
        multimodal_output = _voice_payload(request)
    return _cv.talker2code2wav_async_chunk(transfer_manager, multimodal_output, request, is_finished)
