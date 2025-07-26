from dotenv import load_dotenv
import asyncio
import struct
import pvporcupine
import pyaudio
import os
import speech_recognition as sr
import json
from threading import Thread, Lock
import queue

from livekit import agents
from livekit.agents import AgentSession, Agent, RoomInputOptions
from livekit.plugins import noise_cancellation
from livekit.plugins import google
from prompts import AGENT_INSTRUCTION, SESSION_INSTRUCTION

# OpenAI import removed - using hybrid routing instead

# Import Redis Memory System
from jarvis_memory import JarvisMemory

# Import Local Intent Parser
from local_intent_parser import LocalIntentParser

# Import all tools from tools package
from tools.web_utils import get_weather, search_web, get_current_time, get_current_date, get_current_datetime
from tools.os_commands import (
    send_email, 
    open_application, 
    close_application, 
    find_app_paths, 
    open_file,
    run_command
)
from tools.mouse_key import (
    move_cursor,
    click_mouse,
    scroll_mouse,
    type_text,
    press_key,
    get_cursor_position
)
from tools.interview import (
    start_interview_session,
    set_resume_path,
    tell_about_yourself,
    setup_interview,
    get_next_question,
    submit_answer,
    check_code_solution,
    evaluate_interview
)
from tools.screen import take_screenshot, get_screen_size, read_screen
from tools.audio_control import adjust_volume

# Load .env variables
load_dotenv()

# OpenAI client removed - using hybrid routing instead

# Initialize Redis Memory System (only for user preferences)
memory = JarvisMemory(
    redis_host=os.getenv("REDIS_HOST", "localhost"),
    redis_port=int(os.getenv("REDIS_PORT", 6379)),
    redis_db=int(os.getenv("REDIS_DB", 0))
)

# Initialize Local Intent Parser
try:
    intent_parser = LocalIntentParser(model_path="./intent_model/")
    print("Local intent parser loaded successfully!")
except Exception as e:
    print(f"Error loading local intent parser: {e}")
    intent_parser = None

# --------------------------------------------- 
# Speech-to-Text Handler
# --------------------------------------------- 
class STTHandler:
    def __init__(self):
        self.recognizer = sr.Recognizer()
        self.microphone = sr.Microphone()
        self.audio_queue = queue.Queue()
        self.is_listening = False
        self.lock = Lock()
        
        # Adjust for ambient noise
        print("Calibrating microphone for ambient noise...")
        with self.microphone as source:
            self.recognizer.adjust_for_ambient_noise(source)
        print("Microphone calibrated.")
    
    def start_listening(self):
        if self.is_listening:
            print("Already listening. Ignoring start request.")
            return
        self.is_listening = True
        listen_thread = Thread(target=self._listen_loop, daemon=True)
        listen_thread.start()

    def stop_listening(self):
        if not self.is_listening:
            print("Not listening. Nothing to stop.")
            return
        self.is_listening = False
    
    def _listen_loop(self):
        """Continuous listening loop"""
        while self.is_listening:
            try:
                with self.microphone as source:
                    audio = self.recognizer.listen(source, timeout=1, phrase_time_limit=2)
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
                # Use Google Speech Recognition (free tier) with timeout
                text = await asyncio.wait_for(
                    asyncio.get_event_loop().run_in_executor(
                        None, self.recognizer.recognize_google, audio
                    ),
                    timeout=2.0  # 2 second timeout for faster response
                )
                return text.lower()
        except sr.UnknownValueError:
            return None
        except sr.RequestError as e:
            print(f"Speech recognition error: {e}")
            return None
        except queue.Empty:
            return None
        except asyncio.TimeoutError:
            print("Speech recognition timed out")
            return None
        return None

# --------------------------------------------- 
# Local Function Parser with Memory
# --------------------------------------------- 
class LocalFunctionParser:
    def __init__(self, intent_parser: LocalIntentParser, memory_system: JarvisMemory):
        self.intent_parser = intent_parser
        self.memory = memory_system
        self.available_functions = {
            "get_weather": get_weather,
            "search_web": search_web,
            "send_email": send_email,
            "open_application": open_application,
            "close_application": close_application,
            "find_application": find_app_paths,
            "open_file": open_file,
            "run_command": run_command,
            "move_cursor": move_cursor,
            "click_mouse": click_mouse,
            "scroll_mouse": scroll_mouse,
            "type_text": type_text,
            "press_key": press_key,
            "adjust_volume": adjust_volume,
            "take_screenshot": take_screenshot,
            "get_cursor_position": get_cursor_position,
            "get_screen_size": get_screen_size,
            "get_current_time": get_current_time,
            "get_current_date": get_current_date,
            "get_current_datetime": get_current_datetime,
            "read_screen": read_screen,
            "start_interview_session": start_interview_session,
            "get_next_question": get_next_question,
            "submit_answer": submit_answer,
            "set_resume_path": set_resume_path,
            "tell_about_yourself": tell_about_yourself,
            "setup_interview": setup_interview,
            "evaluate_interview": evaluate_interview,
            "check_code_solution": check_code_solution
        }
    
    async def try_parse_tool(self, text: str) -> bool:
        """Try to parse as a tool call - returns True if successful, False if should fall back to LLM"""
        if not self.intent_parser:
            return False
        
        try:
            function_call = self.intent_parser.parse_and_extract_function(text)
            
            if function_call and function_call.get("function_name"):
                await self._execute_function(function_call, None, None, text)
                return True
            else:
                return False  # No tool detected, use LLM
                
        except Exception as e:
            print(f"Error in local parsing: {e}")
            return False  # Fall back to LLM on error
    
    async def _execute_function(self, function_call: dict, session, room_id: str, original_command: str):
        """Execute the parsed function and store in memory"""
        function_name = function_call.get("function_name")
        parameters = function_call.get("parameters", {})
        confidence = function_call.get("confidence", 0.0)
        
        if function_name in self.available_functions:
            try:
                # Create a mock context for the function
                class MockContext:
                    pass
                
                mock_context = MockContext()
                
                print(f"Executing {function_name} with parameters: {parameters} (confidence: {confidence:.3f})")
                
                # Execute the function with mock context
                result = await self.available_functions[function_name](mock_context, **parameters)
                
                print(f"Function {function_name} executed successfully: {result}")
                
                # Only log usage metrics (no conversation storage)
                self.memory.increment_usage_metric(f"function_{function_name}")
                
                print(f"Function executed successfully: {result}")
                
            except Exception as e:
                error_msg = f"Error executing {function_name}: {str(e)}"
                print(f"{error_msg}")
        else:
            print(f"Unknown function: {function_name}")

# --------------------------------------------- 
# Hybrid Smart Routing (now integrated into Agent.on_user_turn_completed)
# --------------------------------------------- 

# --------------------------------------------- 
# Enhanced LiveKit Agent with Memory
# --------------------------------------------- 
class JarvisAgent(Agent):
    def __init__(self, memory_system: JarvisMemory):
        self.memory = memory_system
        
        # Get user preferences for voice settings
        voice_preference = self.memory.get_user_preference("voice", None)
        selected_voice = voice_preference if voice_preference else "Aoede"
        
        super().__init__(
            instructions=AGENT_INSTRUCTION,
            llm=google.beta.realtime.RealtimeModel(
                voice=selected_voice,
                temperature=0.8,
            ),
            tools=[
                get_weather,
                search_web,
                send_email,
                open_application,
                close_application,
                find_app_paths,
                open_file,
                run_command,
                move_cursor,
                click_mouse,
                scroll_mouse,
                type_text,
                press_key,
                adjust_volume,
                take_screenshot,
                get_cursor_position,
                get_screen_size,
                get_current_time,
                get_current_date,
                get_current_datetime,
                read_screen,
                start_interview_session,
                set_resume_path,
                tell_about_yourself,
                setup_interview,
                get_next_question,
                submit_answer,
                check_code_solution,
                evaluate_interview
            ],
        )

# --------------------------------------------- 
# OpenAI Text-to-Speech Handler (DISABLED - using LiveKit)
# --------------------------------------------- 
async def play_openai_tts(text: str, voice: str = "onyx"):
    """Play text using OpenAI's TTS with Jarvis-like voice"""
    try:
        import pygame
        import tempfile
        
        # Generate speech using OpenAI TTS (async to avoid blocking)
        loop = asyncio.get_event_loop()
        response = await loop.run_in_executor(
            None,
            lambda: openai_client.audio.speech.create(
                model="tts-1-hd",  # or "tts-1-hd" for higher quality
                voice="onyx",    # onyx = deep male voice (Jarvis-like)
                input=text,
                speed=1.0
            )
        )
        
        # Save to temporary file
        with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as tmp_file:
            tmp_file.write(response.content)
            tmp_filename = tmp_file.name
        
        # Play the audio (async to avoid blocking)
        await loop.run_in_executor(None, _play_audio_sync, tmp_filename)
        
        # Cleanup
        await loop.run_in_executor(None, os.unlink, tmp_filename)
        
        print(f"Played TTS: {text[:50]}...")
        
    except ImportError:
        print("Warning: pygame not installed. Install with: pip install pygame")
        print(f"Text only: {text}")
    except Exception as e:
        print(f"TTS error: {e}")
        print(f"Text only: {text}")

def _play_audio_sync(filename):
    """Synchronous audio playback in thread"""
    try:
        import pygame
        pygame.mixer.init()
        pygame.mixer.music.load(filename)
        pygame.mixer.music.play()
        
        while pygame.mixer.music.get_busy():
            time.sleep(0.1)
        
        pygame.mixer.quit()
    except Exception as e:
        print(f"Audio playback error: {e}")

# --------------------------------------------- 
# OpenAI + Gemini Voice Handler (DISABLED - using hybrid routing)
# --------------------------------------------- 
async def handle_openai_with_voice(transcription: str, session, room_id: str = None):
    """Generate response with OpenAI, then use Gemini voice synthesis"""
    try:
        # Get conversation context from memory
        context = memory.get_context("conversation_history", room_id) or []
        
        # Add user message to context
        context.append({"role": "user", "content": transcription})
        
        # Keep only last 10 messages for context
        if len(context) > 10:
            context = context[-10:]
        
        # Create OpenAI chat completion
        response = openai_client.chat.completions.create(
            model="gpt-4o", 
            messages=[
                {"role": "system", "content": AGENT_INSTRUCTION},
                *context
            ],
            temperature=0.7,
            max_tokens=150
        )
        
        ai_response = response.choices[0].message.content
        
        # Add AI response to context
        context.append({"role": "assistant", "content": ai_response})
        
        # Store updated context
        memory.set_context("conversation_history", context, expiry_minutes=60, room_id=room_id)
        
        print(f"OpenAI response: {ai_response}")
        
        # Use OpenAI TTS for reliable voice synthesis
        await play_openai_tts(ai_response)
        
        # Also try Gemini voice as backup if available
        if session:
            try:
                await session.generate_reply(instructions=ai_response)
            except:
                pass  # Gemini failed, but OpenAI TTS already played
        
    except Exception as e:
        print(f"OpenAI error: {e}")
        # Final fallback
        if session:
            await session.generate_reply(instructions="I'm having trouble processing that right now. Could you try again?")
        else:
            print("I'm having trouble processing that right now. Could you try again?")

# --------------------------------------------- 
# OpenAI Backup Handler (DISABLED - using hybrid routing)
# --------------------------------------------- 
async def handle_openai_backup(transcription: str, session, room_id: str = None):
    """Handle conversation using OpenAI as backup"""
    try:
        # Get conversation context from memory
        context = memory.get_context("conversation_history", room_id) or []
        
        # Add user message to context
        context.append({"role": "user", "content": transcription})
        
        # Keep only last 10 messages for context
        if len(context) > 10:
            context = context[-10:]
        
        # Create OpenAI chat completion
        response = openai_client.chat.completions.create(
            model="gpt-4o", 
            messages=[
                {"role": "system", "content": AGENT_INSTRUCTION},
                *context
            ],
            temperature=0.7,
            max_tokens=150
        )
        
        ai_response = response.choices[0].message.content
        
        # Add AI response to context
        context.append({"role": "assistant", "content": ai_response})
        
        # Store updated context
        memory.set_context("conversation_history", context, expiry_minutes=60, room_id=room_id)
        
        # Send response through LiveKit session
        await session.generate_reply(instructions=ai_response)
        
        print(f"OpenAI backup response: {ai_response}")
        
    except Exception as e:
        print(f"OpenAI backup error: {e}")
        # Final fallback
        await session.generate_reply(instructions="I'm having trouble processing that right now. Could you try again?")

# --------------------------------------------- 
# Memory Command Handler
# --------------------------------------------- 
async def handle_memory_commands(transcription: str, session, room_id: str = None) -> bool:
    """Handle special memory-related commands"""
    text = transcription.lower()
    
    # Remember something
    if text.startswith("remember that") or text.startswith("remember this"):
        memory_text = text.replace("remember that", "").replace("remember this", "").strip()
        memory.set_context("user_note", memory_text, expiry_minutes=1440, room_id=room_id)  # 24 hours
        if session:
            await session.generate_reply(instructions=f"I'll remember that: {memory_text}")
        else:
            print(f"Remembered: {memory_text}")
        return True
    
    # Recall something
    elif "what do you remember" in text or "what did i tell you to remember" in text:
        user_note = memory.get_context("user_note", room_id)
        response = f"You told me to remember: {user_note}" if user_note else "I don't have any specific notes to remember right now."
        if session:
            await session.generate_reply(instructions=response)
        else:
            print(response)
        return True
    
    # Clear memory
    elif "forget everything" in text or "clear memory" in text:
        memory.clear_context(room_id=room_id)
        if session:
            await session.generate_reply(instructions="I've cleared my memory context.")
        else:
            print("Memory context cleared")
        return True
    
    # Memory status
    elif any(phrase in text for phrase in [
        "memory status",
        "what is your memory status",
        "how is your memory",
        "what's your memory"
    ]):
        status = memory.get_memory_status()
        if session:
            await session.generate_reply(instructions=f"Memory status: {status}")
        else:
            print(f"Memory status: {status}")
        return True
    
    # Set preference
    elif text.startswith("set preference") or text.startswith("i prefer"):
        # Simple preference setting 
        if "voice" in text:
            if "aoede" in text:
                memory.set_user_preference("voice", "Aoede", room_id)
                if session:
                    await session.generate_reply(instructions="I've set your voice preference to Aoede.")
                else:
                    print("Voice preference set to Aoede")
        return True
    
    
    # Show recent commands
    elif any(phrase in text for phrase in [
        "show recent commands", 
        "show me recent commands", 
        "show my recent commands", 
        "recent commands", 
        "what have i asked you to do"
    ]):
        recent_commands = memory.get_recent_commands(5, room_id)
        if recent_commands:
            commands_text = "Recent commands:\n"
            for cmd in recent_commands:
                commands_text += f"- {cmd['command']} → {cmd['function_name']}\n"
            if session:
                await session.generate_reply(instructions=commands_text)
            else:
                print(commands_text)
        else:
            if session:
                await session.generate_reply(instructions="No recent commands to show.")
            else:
                print("No recent commands to show")
        return True
    
    # Model performance info
    elif any(phrase in text for phrase in [
        "model performance",
        "intent model status",
        "classification performance",
        "how accurate is your model"
    ]):
        if intent_parser:
            await session.generate_reply(instructions="Local intent classification model is active with 98.5% accuracy and 100% test performance. All 13 intents are supported with high confidence detection.")
        else:
            await session.generate_reply(instructions="Local intent parser is not available.")
        return True
    
    return False

# --------------------------------------------- 
# Enhanced Wake Word Detection with Local Intent Parser
# --------------------------------------------- 
async def listen_for_wake_word_and_respond(session, room_id: str = None, stt_handler=None, function_parser=None):
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
    
    # Use provided instances or create new ones (fallback for backwards compatibility)
    if stt_handler is None:
        stt_handler = STTHandler()
    if function_parser is None:
        function_parser = LocalFunctionParser(intent_parser, memory)
    
    print("Wake word listener running with LOCAL intent classification.")
    print("Local model accuracy: 98.5% with 100% test performance")
    print(f"Memory system status: {memory.get_memory_status()}")
    
    try:
        while True:
            pcm = stream.read(porcupine.frame_length, exception_on_overflow=False)
            pcm = struct.unpack_from("h" * porcupine.frame_length, pcm)
            result = porcupine.process(pcm)
            
            if result >= 0:
                print("Wake word 'Jarvis' detected! Starting speech recognition...")
                
                # Increment wake word metric
                memory.increment_usage_metric("wake_word_triggered")
                
                # Start listening for speech
                stt_handler.start_listening()
                
                # Wait for speech input (with timeout)
                speech_detected = False
                timeout_counter = 0
                max_timeout = 10  # 1 second timeout for faster response
                
                while not speech_detected and timeout_counter < max_timeout:
                    transcription = await stt_handler.get_transcription()
                    if transcription:
                        print(f"Transcribed: '{transcription}'")
                        
                        # Try local parser first, then fallback to LiveKit
                        tool_handled = await function_parser.try_parse_tool(transcription)
                        if not tool_handled:
                            await session.generate_reply(instructions=transcription)
                        speech_detected = True
                        break  # Exit immediately after processing
                    
                    await asyncio.sleep(0.1)
                    timeout_counter += 1
                
                # Stop listening after processing
                stt_handler.stop_listening()
                
                if not speech_detected:
                    print("No speech detected within timeout")
                    if session:
                        await session.generate_reply(instructions="I'm listening, but didn't hear anything. Please try again.")
                    else:
                        print("No speech detected within timeout period")
                
                # Brief pause before listening for next wake word
                await asyncio.sleep(0.5)
                
    except KeyboardInterrupt:
        print("\nStopping wake word listener...")
    except Exception as e:
        print(f"Error in wake word listener: {e}")
    finally:
        # Cleanup
        stream.stop_stream()
        stream.close()
        pa.terminate()
        porcupine.delete()
        stt_handler.stop_listening()

# --------------------------------------------- 
# Main Agent Session Handler
# --------------------------------------------- 
async def entrypoint(ctx: agents.JobContext):
    """Main entry point for the agent"""
    # Create LiveKit session (like your working code)
    session = AgentSession()

    await session.start(
        room=ctx.room,
        agent=JarvisAgent(memory),
        room_input_options=RoomInputOptions(
            video_enabled=True,
            noise_cancellation=noise_cancellation.BVC(),
        ),
    )

    await ctx.connect()

    # Initial greeting
    await session.generate_reply(instructions=SESSION_INSTRUCTION)
    
    print("LiveKit agent ready with Redis memory and local parser for wake word system")


# --------------------------------------------- 
# Entry Point
# --------------------------------------------- 
if __name__ == "__main__":
    agents.cli.run_app(agents.WorkerOptions(entrypoint_fnc=entrypoint))