"""Long replies: the talker speaks them in segments, each with a fresh LM context.

The tag-tts talker LM degrades after ~55-60 s of continuous speech context. So after about SEEK_S seconds of text the
talker ends the current segment at the next sentence end (FORCE_S: at a comma / where it is), and the *same* request
starts again from its prompt on the rest of the text. The thinker, the request and the client stream do not change; the
flow / HiFT stage gets one continuous token stream with the same voice prompt.

The talker (talker_tag.py) decides the cut and puts the request id in PENDING. This module patches the talker stage
(all of it runs in that stage's EngineCore process):
1. scheduler: restart PENDING requests with vLLM's own preemption-and-recompute (Scheduler._preempt_request), after
   cutting the token history back to the prompt -- the request mutation vLLM-Omni uses for a replaced streaming prompt;
2. model runner: drop the cached output tokens of a restarted request;
3. chunk receiver: in async-chunk mode the talker steps only when a new chunk from the thinker has arrived, so with many
   long replies at once the thinker's pace stalls the speech. While the talker has AHEAD_MIN text tokens in hand it keeps
   stepping; when it runs low it waits for chunks as before (those that piled up are already there).
The talker -> code2wav chunker (proc.py) prepends request._sophon_prev_out, so it still reads one continuous stream."""
from __future__ import annotations

import os
import time

SEEK_S = float(os.environ.get("SOPHON_SEG_SEEK_S", "25"))      # from here, end the segment at the next sentence end
FORCE_S = float(os.environ.get("SOPHON_SEG_FORCE_S", "40"))    # no sentence end by here: end it at a comma / now
AHEAD_MIN = int(os.environ.get("SOPHON_TALKER_AHEAD", "10"))   # text tokens in hand to keep stepping without a chunk

PENDING: set[str] = set()      # talker -> scheduler: restart these requests
AHEAD: dict[str, int] = {}     # talker -> chunk receiver: text tokens received but not yet fed
_CLEAR: set[str] = set()       # scheduler -> model runner: drop the cached outputs of these requests
_installed = False


def install(log) -> None:
    global _installed
    if _installed:
        return
    _installed = True
    from vllm.v1.request import RequestStatus
    from vllm_omni.core.sched.omni_ar_scheduler import OmniARScheduler
    from vllm_omni.distributed.omni_connectors.transfer_adapter.chunk_transfer_adapter import OmniChunkTransferAdapter
    from vllm_omni.worker.gpu_model_runner import GPUModelRunner

    schedule = OmniARScheduler.schedule

    def restart_then_schedule(self, *a, **k):
        for rid in list(PENDING):
            req = self.requests.get(rid)
            if req is None:
                PENDING.discard(rid)
            elif req.status == RequestStatus.RUNNING and req in self.running:     # else (parked for a chunk): next step
                PENDING.discard(rid)
                self.running.remove(req)
                self._preempt_request(req, time.monotonic(), drop_stale_output=True)
                req._sophon_prev_out = tuple(getattr(req, "_sophon_prev_out", ())) + tuple(req._output_token_ids)
                del req._all_token_ids[req.num_prompt_tokens:]
                req._output_token_ids.clear()
                # the chunk sender's "already sent" mark counts this request's tokens: reset it with them
                self.chunk_transfer_adapter.requests_num_chunks_sent.pop(req.external_req_id, None)
                _CLEAR.add(rid)
                log.info("sophon talker: new segment for %s", rid)
        return schedule(self, *a, **k)

    OmniARScheduler.schedule = restart_then_schedule

    update_states = GPUModelRunner._update_states

    def clear_then_update(self, scheduler_output):
        for rid in list(_CLEAR):
            _CLEAR.discard(rid)
            if rid in self.requests:
                self.requests[rid].output_token_ids = []
        return update_states(self, scheduler_output)

    GPUModelRunner._update_states = clear_then_update

    process_queue = OmniChunkTransferAdapter._process_chunk_queue_legacy

    def process_queue_unless_ahead(self, queue, waiting_list, target_status, finished_load_reqs):
        ahead = []
        if target_status == RequestStatus.RUNNING:
            ahead = [r for r in queue if AHEAD_MIN > 0 and AHEAD.get(r.request_id, 0) >= AHEAD_MIN and r.status == RequestStatus.RUNNING
                     and r.request_id not in self.requests_with_ready_chunks]
            for r in ahead:
                queue.remove(r)
        process_queue(self, queue, waiting_list, target_status, finished_load_reqs)
        queue.extend(ahead)

    OmniChunkTransferAdapter._process_chunk_queue_legacy = process_queue_unless_ahead
    log.info("sophon talker: long replies in segments (seek %.0f s, force %.0f s), steps ahead with %d tokens in hand",
             SEEK_S, FORCE_S, AHEAD_MIN)
