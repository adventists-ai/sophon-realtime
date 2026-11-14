"""Sophon Realtime on a Mac, served over a WebSocket: a network device supplies the microphone and the speaker.

The wire format is the simplest one a small device can speak. Binary frames are raw PCM16 mono audio at --rate, in both directions. A text frame {"type": "interrupt"} means "stop talking now": the server sends it when the user barges in, so the client can drop audio it has buffered, and a client may send it to cut the reply itself (a wake word spoken over the reply, for example). With --events the server also sends the engine's own events (reply_start, first_audio, reply_done, barge_in, ...) as text frames.

The client is expected to cancel its own echo (a headset, or a device with hardware echo cancellation), so none is done here. One conversation at a time: a second client is refused while one is connected.

    python serve.py --host ADDRESS [--port 8765] [--rate 24000] [--lang zh|en] [--voice chelsie] [--events]"""
import argparse, asyncio, json, os, sys
import numpy as np, websockets
from scipy.signal import resample_poly
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path[:0] = [HERE, os.path.dirname(HERE)]
from engine import Brain, Session, SR

ap = argparse.ArgumentParser()
ap.add_argument("--root", default=os.environ.get("SOPHON_MODELS", os.path.join(os.path.dirname(HERE), "models")))
ap.add_argument("--lang", default="zh"); ap.add_argument("--voice", default="chelsie")
ap.add_argument("--host", required=True, help="address to listen on; there is no authentication, so name one interface's address")
ap.add_argument("--port", type=int, default=8765)
ap.add_argument("--rate", type=int, default=24000, help="sample rate of the client's PCM16 audio, both directions")
ap.add_argument("--events", action="store_true", help="also send the engine's events to the client as text frames")
a = ap.parse_args()

FR = 320                      # the engine takes 20 ms frames at 16 kHz
OUT_RATE = 24000              # the engine's reply audio
INTERRUPT = json.dumps({"type": "interrupt"})
busy = False


def to_pcm(x):
    y = np.asarray(x, np.float32)
    if a.rate != OUT_RATE: y = resample_poly(y, a.rate, OUT_RATE)
    return (np.clip(y, -1.0, 1.0) * 32767.0).astype("<i2").tobytes()


async def handle(ws):
    global busy
    if busy:
        await ws.close(1013, "one conversation at a time"); return
    busy = True
    loop = asyncio.get_running_loop(); out = asyncio.Queue()

    def play(x):
        """Called by the engine's worker thread with 24 kHz reply audio, or None to stop at once (barge-in)."""
        loop.call_soon_threadsafe(out.put_nowait, None if x is None else to_pcm(x))

    def log(m):
        if a.events: loop.call_soon_threadsafe(out.put_nowait, m)

    async def send():
        while True:
            m = await out.get()
            if m is None:
                kept = []                                   # audio queued before the cut is never sent; events are
                while not out.empty():
                    q = out.get_nowait()
                    if isinstance(q, str): kept.append(q)
                await ws.send(INTERRUPT)
                for q in kept: await ws.send(q)
            else:
                await ws.send(m)

    sess = Session(brain, play, log=log); sender = asyncio.ensure_future(send()); buf = np.zeros(0, np.float32)
    try:
        async for m in ws:
            if isinstance(m, str):
                try: kind = json.loads(m).get("type")
                except (ValueError, AttributeError): kind = None
                if kind == "interrupt":
                    with sess.lock: sess._onset()
                continue
            x = np.frombuffer(m[: len(m) // 2 * 2], "<i2").astype(np.float32) / 32768.0
            if a.rate != SR: x = resample_poly(x, SR, a.rate).astype(np.float32)
            buf = np.concatenate([buf, x])
            while len(buf) >= FR:
                f, buf = buf[:FR], buf[FR:]
                sess.feed(f)
    except websockets.ConnectionClosed:
        pass
    finally:
        with sess.lock:
            if sess.reply is not None: sess.reply["cancel"] = True
        sender.cancel(); busy = False


async def main():
    async with websockets.serve(handle, a.host, a.port, max_size=1 << 20):
        print(f"Listening on ws://{a.host}:{a.port} (PCM16 mono at {a.rate} Hz). Ctrl+C to quit.", flush=True)
        await asyncio.Future()


print("Loading the model (first time ~1 min)...", flush=True)
brain = Brain(a.root, lang=a.lang, voice=a.voice, sys_prompt=os.path.join(HERE, "system_prompt.json")); brain.warmup()
try:
    asyncio.run(main())
except KeyboardInterrupt:
    print("\nBye.", flush=True)
    os._exit(0)          # skip interpreter teardown (MLX streams owned by the worker thread would complain)
