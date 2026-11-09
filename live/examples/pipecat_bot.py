"""Pipecat pipeline backed by a self-hosted Sophon-Realtime model.

The Live gateway speaks the OpenAI Realtime protocol, so Pipecat's OpenAIRealtimeLLMService works unchanged:
point it at the gateway with base_url (a ws:// URL ending in /v1/realtime).

  pip install "pipecat-ai[openai,webrtc]"
  # engine + gateway on YOUR_SERVER (see ../README.md):
  #   sophon-realtime serve --port 8000
  #   BUILD=tag PORT=8000 LIVE_PORT=8780 bash ../start_live.sh

Tested with pipecat-ai 1.15.0: reply text and audio stream back.
Drop `llm` into any Pipecat transport pipeline (Daily, WebRTC, Twilio, ...) exactly where you would put OpenAI Realtime:

    pipeline = Pipeline([transport.input(), llm, transport.output()])
"""
import os

from pipecat.services.openai.realtime.llm import OpenAIRealtimeLLMService

llm = OpenAIRealtimeLLMService(
    api_key=os.environ.get("SOPHON_API_KEY", "any"),               # one of SOPHON_LIVE_REALTIME_KEYS if you set keys
    base_url=os.environ.get("SOPHON_URL", "ws://YOUR_SERVER:8780/v1/realtime"),
    model="sophon-realtime",
)
