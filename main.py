from dotenv import load_dotenv
import asyncio
import struct
import pvporcupine
import pyaudio
import os
import speech_recognition as sr
import json
import openai
from threading import Thread
import queue

from livekit import agents
from livekit.agents import AgentSession, Agent, RoomInputOptions
from livekit.plugins import noise_cancellation
from livekit.plugins import google
from prompts import AGENT_INSTRUCTION, SESSION_INSTRUCTION, FUNCTION_PARSER_PROMPT
from tools import get_weather, search_web, send_email

# Load .env variables
load_dotenv()

# Initialize OpenAI
openai.api_key = os.getenv("OPENAI_API_KEY")

# --------------------------------------------- 
# Speech-to-Text Handler
# --------------------------------------------- 
class STTHandler:
    def __init__(self):
        self.recognizer = sr.Recognizer()
        self.microphone = sr.Microphone()
        self.audio_queue = queue.Queue()
        self.is_listening = False
        
        # Adjust for ambient noise
        print("Calibrating microphone for ambient noise...")
        with self.microphone as source:
            self.recognizer.adjust_for_ambient_noise(source)
        print("Microphone calibrated.")
    
    def start_listening(self):
        """Start continuous listening for speech"""
        self.is_listening = True
        listen_thread = Thread(target=self._listen_loop, daemon=True)
        listen_thread.start()
    
    def stop_listening(self):
        """Stop listening for speech"""
        self.is_listening = False
    
    def _listen_loop(self):
        """Continuous listening loop"""
        while self.is_listening:
            try:
                with self.microphone as source:
                    # Listen for audio with timeout
                    audio = self.recognizer.listen(source, timeout=1, phrase_time_limit=5)
                    self.audio_queue.put(audio)
            except sr.WaitTimeoutError:
                continue
            except Exception as e:
                print(f"Error in listening loop: {e}")
    
    async def get_transcription(self):
        """Get transcription from audio queue"""
        try:
            if not self.audio_queue.empty():
                audio = self.audio_queue.get_nowait()
                # Use Google Speech Recognition (free tier)
                text = self.recognizer.recognize_google(audio)
                return text.lower()
        except sr.UnknownValueError:
            return None
        except sr.RequestError as e:
            print(f"Speech recognition error: {e}")
            return None
        except queue.Empty:
            return None
        return None

# --------------------------------------------- 
# Function Parser using OpenAI
# --------------------------------------------- 
class FunctionParser:
    def __init__(self):
        self.available_functions = {
            "get_weather": get_weather,
            "search_web": search_web,
            "send_email": send_email
        }
    
    async def parse_and_execute(self, text: str, session):
        """Parse text for function calls and execute them"""
        try:
            # Use OpenAI to parse the text and extract function calls
            response = openai.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": FUNCTION_PARSER_PROMPT},
                    {"role": "user", "content": text}
                ],
                temperature=0.1
            )
            
            result = response.choices[0].message.content.strip()
            
            # Try to parse as JSON
            try:
                function_call = json.loads(result)
                if function_call.get("function_name") and function_call.get("function_name") != "none":
                    await self._execute_function(function_call, session)
                    return True
            except json.JSONDecodeError:
                # If not JSON, check if it's a "none" response
                if result.lower() == "none":
                    return False
                    
        except Exception as e:
            print(f"Error parsing function: {e}")
            return False
        
        return False
    
    async def _execute_function(self, function_call: dict, session):
        """Execute the parsed function"""
        function_name = function_call.get("function_name")
        parameters = function_call.get("parameters", {})
        
        if function_name in self.available_functions:
            try:
                # Create a mock context for the function
                class MockContext:
                    pass
                
                mock_context = MockContext()
                
                # Execute the function
                if function_name == "get_weather":
                    result = await self.available_functions[function_name](mock_context, **parameters)
                elif function_name == "search_web":
                    result = await self.available_functions[function_name](mock_context, **parameters)
                elif function_name == "send_email":
                    result = await self.available_functions[function_name](mock_context, **parameters)
                
                print(f"Function {function_name} executed: {result}")
                
                # Send result back to assistant
                await session.generate_reply(instructions=f"The function {function_name} was executed with result: {result}")
                
            except Exception as e:
                error_msg = f"Error executing {function_name}: {str(e)}"
                print(f"{error_msg}")
                await session.generate_reply(instructions=f"There was an error: {error_msg}")
        else:
            print(f"Unknown function: {function_name}")

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
# Async Wake Word Detection and STT Loop
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
    
    # Initialize STT handler and function parser
    stt_handler = STTHandler()
    function_parser = FunctionParser()
    
    print("Wake word listener running. Say 'Jarvis' anytime to trigger the assistant.")
    
    try:
        while True:
            pcm = stream.read(porcupine.frame_length, exception_on_overflow=False)
            pcm = struct.unpack_from("h" * porcupine.frame_length, pcm)
            result = porcupine.process(pcm)
            
            if result >= 0:
                print("Wake word 'Jarvis' detected! Starting speech recognition...")
                
                # Start listening for speech
                stt_handler.start_listening()
                
                # Wait for speech input (with timeout)
                speech_detected = False
                timeout_counter = 0
                max_timeout = 50  # 5 seconds timeout
                
                while not speech_detected and timeout_counter < max_timeout:
                    transcription = await stt_handler.get_transcription()
                    if transcription:
                        print(f"🎤 Transcribed: '{transcription}'")
                        
                        # Parse for function calls
                        function_executed = await function_parser.parse_and_execute(transcription, session)
                        
                        # If no function was executed, send to normal assistant
                        if not function_executed:
                            await session.generate_reply(instructions=f"User said: '{transcription}'. {SESSION_INSTRUCTION}")
                        
                        speech_detected = True
                    else:
                        await asyncio.sleep(0.1)
                        timeout_counter += 1
                
                # Stop listening
                stt_handler.stop_listening()
                
                if not speech_detected:
                    print("⏰ No speech detected within timeout period")
                    await session.generate_reply(instructions="I didn't hear anything, sir. How may I assist you?")
            
            await asyncio.sleep(0)  # yield control to event loop
    
    except Exception as e:
        print(f"Wake word error: {e}")
    
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