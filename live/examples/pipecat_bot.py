"""Pipecat voice bot backed by a self-hosted Sophon-Realtime model.

The Sophon-Realtime Live gateway speaks the OpenAI Realtime protocol, so Pipecat's built-in
OpenAIRealtimeLLMService works unchanged: point base_url at your gateway. No extra package.

Server (one 80 GB GPU, see ../README.md):
    pip install sophon-realtime && sophon-realtime serve --port 8000
    BUILD=tag PORT=8000 LIVE_PORT=8780 bash ../start_live.sh

Bot:
    uv add "pipecat-ai[openai,webrtc,runner]"
    SOPHON_URL=ws://YOUR_SERVER:8780/v1/realtime python pipecat_bot.py
    # then open http://localhost:7860/client in a browser and talk

Tested with Pipecat v1.15.0. Maintained by Adventists AI (the Sophon-Realtime authors).
"""

import os

from dotenv import load_dotenv
from loguru import logger

from pipecat.pipeline.pipeline import Pipeline
from pipecat.pipeline.worker import PipelineParams, PipelineWorker
from pipecat.runner.types import RunnerArguments
from pipecat.runner.utils import create_transport
from pipecat.services.openai.realtime.llm import OpenAIRealtimeLLMService
from pipecat.transports.base_transport import BaseTransport, TransportParams
from pipecat.workers.runner import WorkerRunner

load_dotenv(override=True)

SOPHON_URL = os.getenv("SOPHON_URL", "ws://localhost:8780/v1/realtime")

# Local WebRTC for development. Daily, LiveKit and Twilio transports work the same way
# (see the transport_params pattern in Pipecat's examples/realtime/realtime-openai.py).
transport_params = {
    "webrtc": lambda: TransportParams(audio_in_enabled=True, audio_out_enabled=True),
}


async def run_bot(transport: BaseTransport, runner_args: RunnerArguments):
    """Run a speech-to-speech bot: user audio goes to Sophon-Realtime, its voice comes back."""
    llm = OpenAIRealtimeLLMService(
        api_key=os.getenv("SOPHON_API_KEY", "any"),  # a key from SOPHON_LIVE_REALTIME_KEYS_FILE, if you set one
        base_url=SOPHON_URL,
        model="sophon-realtime",
        settings=OpenAIRealtimeLLMService.Settings(
            system_instruction="You are a friendly voice assistant. Keep replies to one or two short sentences.",
        ),
    )

    # Sophon-Realtime runs turn-taking server-side (full duplex): it listens while it talks
    # and decides when to answer, so no local VAD or turn analyzer is needed.
    pipeline = Pipeline([transport.input(), llm, transport.output()])
    worker = PipelineWorker(pipeline, params=PipelineParams(enable_metrics=True), idle_timeout_secs=runner_args.pipeline_idle_timeout_secs)
    runner = WorkerRunner(handle_sigint=runner_args.handle_sigint)
    await runner.add_workers(worker)

    @transport.event_handler("on_client_connected")
    async def on_client_connected(transport, client):
        logger.info("Client connected: start talking")

    @transport.event_handler("on_client_disconnected")
    async def on_client_disconnected(transport, client):
        logger.info("Client disconnected")
        await runner.cancel()

    await runner.run()


async def bot(runner_args: RunnerArguments):
    """Entry point for the Pipecat development runner."""
    transport = await create_transport(runner_args, transport_params)
    await run_bot(transport, runner_args)


if __name__ == "__main__":
    from pipecat.runner.run import main

    main()
