from dotenv import load_dotenv
import asyncio
import struct
import pvporcupine
import pyaudio
import os

from livekit import agents
from livekit.agents import AgentSession, Agent, RoomInputOptions
from livekit.plugins import noise_cancellation
from livekit.plugins import google
from prompts import AGENT_INSTRUCTION, SESSION_INSTRUCTION
from tools import get_weather, search_web, send_email

# Load .env variables
load_dotenv()

# ---------------------------------------------
# LiveKit Agent Definition
# ---------------------------------------------
class Assistant(Agent):
    def __init__(self) -> None:
        super().__init__(
            instructions=AGENT_INSTRUCTION,
            llm=google.beta.realtime.RealtimeModel(
                voice="Aoede",
                temperature=0.8,
            ),
            tools=[
                get_weather,
                search_web,
                send_email
            ],
        )

# ---------------------------------------------
# Async Wake Word Detection Loop
# ---------------------------------------------
async def listen_for_wake_word_and_respond(session):
    access_key = os.environ["PORCUPINE_ACCESS_KEY"]
    porcupine = pvporcupine.create(access_key=access_key, keywords=["jarvis"])

    pa = pyaudio.PyAudio()
    stream = pa.open(
        rate=porcupine.sample_rate,
        channels=1,
        format=pyaudio.paInt16,
        input=True,
        frames_per_buffer=porcupine.frame_length
    )

    print("✅ Wake word listener running. Say 'Jarvis' anytime to trigger the assistant.")

    try:
        while True:
            pcm = stream.read(porcupine.frame_length, exception_on_overflow=False)
            pcm = struct.unpack_from("h" * porcupine.frame_length, pcm)
            result = porcupine.process(pcm)
            if result >= 0:
                print("🟢 Wake word 'Jarvis' detected! Sending prompt to assistant...")
                await session.generate_reply(instructions=SESSION_INSTRUCTION)

            await asyncio.sleep(0)  # yield control to event loop

    except Exception as e:
        print(f"❌ Wake word error: {e}")

    finally:
        stream.stop_stream()
        stream.close()
        pa.terminate()
        porcupine.delete()

# ---------------------------------------------
# LiveKit Entry Point
# ---------------------------------------------
async def entrypoint(ctx: agents.JobContext):
    session = AgentSession()

    await session.start(
        room=ctx.room,
        agent=Assistant(),
        room_input_options=RoomInputOptions(
            video_enabled=True,
            noise_cancellation=noise_cancellation.BVC(),
        ),
    )

    print("LiveKit session started and connected to room.")

    # Start wake word listening in background
    asyncio.create_task(listen_for_wake_word_and_respond(session))

    # Keep the connection alive
    await ctx.connect()

# ---------------------------------------------
# Main
# ---------------------------------------------
if __name__ == "__main__":
    agents.cli.run_app(agents.WorkerOptions(entrypoint_fnc=entrypoint))
