"""LiveKit Agents voice agent backed by a self-hosted Sophon-Realtime model.

The Live gateway speaks the OpenAI Realtime protocol, so LiveKit's own OpenAI plugin works unchanged:
point RealtimeModel at the gateway with base_url.

  pip install "livekit-agents[openai]"
  # engine + gateway on YOUR_SERVER (see ../README.md):
  #   sophon-realtime serve --port 8000
  #   BUILD=tag PORT=8000 LIVE_PORT=8780 bash ../start_live.sh
  python livekit_agent.py dev        # needs LIVEKIT_URL / LIVEKIT_API_KEY / LIVEKIT_API_SECRET

Tested with livekit-agents 1.8.11: reply text and audio stream back.
"""
import os

from livekit import agents
from livekit.agents import Agent, AgentSession
from livekit.plugins import openai

SOPHON_URL = os.environ.get("SOPHON_URL", "http://YOUR_SERVER:8780/v1")      # the Live gateway, not the engine port


async def entrypoint(ctx: agents.JobContext):
    await ctx.connect()
    session = AgentSession(
        llm=openai.realtime.RealtimeModel(
            base_url=SOPHON_URL,
            api_key=os.environ.get("SOPHON_API_KEY", "any"),    # one of SOPHON_LIVE_REALTIME_KEYS if you set keys
            model="sophon-realtime",
            voice="chelsie",
        )
    )
    await session.start(room=ctx.room, agent=Agent(instructions="You are a friendly voice assistant. Keep replies short."))


if __name__ == "__main__":
    agents.cli.run_app(agents.WorkerOptions(entrypoint_fnc=entrypoint))
