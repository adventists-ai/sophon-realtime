"""Local echo cancellation (WebRTC AEC3 via livekit's AudioProcessingModule): lets the user talk over the reply on speakers
without the reply's own sound being heard as the user speaking. Works on 20 ms frames at 16 kHz."""
import numpy as np
from livekit import rtc

SR, F = 16000, 160                     # APM works on 10 ms frames


def _i16(x):
    return (np.clip(x, -1, 1) * 32767).astype(np.int16).tobytes()


class Echo:
    def __init__(self, delay_ms=40, ns=True):
        self.apm = rtc.AudioProcessingModule(echo_cancellation=True, noise_suppression=ns, high_pass_filter=True, auto_gain_control=False)
        self.delay_ms = int(delay_ms)

    def process(self, mic, far):
        """mic, far: 320 float32 samples each (far = what the speaker played in the same 20 ms). Returns the cleaned mic frame."""
        out = np.empty(len(mic), np.float32)
        for s in range(0, len(mic), F):
            fr = rtc.AudioFrame(_i16(far[s:s + F]), SR, 1, F); self.apm.process_reverse_stream(fr)
            self.apm.set_stream_delay_ms(self.delay_ms)
            nf = rtc.AudioFrame(_i16(mic[s:s + F]), SR, 1, F); self.apm.process_stream(nf)
            out[s:s + F] = np.frombuffer(nf.data, np.int16).astype(np.float32) / 32767
        return out
