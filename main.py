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

# Import Redis Memory System
from jarvis_memory import JarvisMemory

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

# Initialize OpenAI
openai.api_key = os.getenv("OPENAI_API_KEY")

# Initialize Redis Memory System
memory = JarvisMemory(
    redis_host=os.getenv("REDIS_HOST", "localhost"),
    redis_port=int(os.getenv("REDIS_PORT", 6379)),
    redis_db=int(os.getenv("REDIS_DB", 0))
)

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
# Enhanced Function Parser with Memory
# --------------------------------------------- 
class FunctionParser:
    def __init__(self, memory_system: JarvisMemory):
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
    
    async def parse_and_execute(self, text: str, session, room_id: str = None):
        """Parse text for function calls and execute them with memory"""
        try:
            # Get conversation context and command patterns from memory
            conversation_context = self.memory.get_conversation_context(room_id)
            command_patterns = self.memory.get_command_patterns(room_id)
            user_preferences = self.memory.get_all_preferences(room_id)
            
            # Enhanced prompt with memory context
            enhanced_prompt = FUNCTION_PARSER_PROMPT
            
            if conversation_context:
                enhanced_prompt += f"\n\nRecent conversation context:\n{conversation_context}"
            
            if command_patterns:
                enhanced_prompt += f"\n\nRecent command patterns:\n{command_patterns}"
            
            if user_preferences:
                enhanced_prompt += f"\n\nUser preferences: {json.dumps(user_preferences)}"
            
            # Use OpenAI to parse the text and extract function calls
            response = openai.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {"role": "system", "content": enhanced_prompt},
                    {"role": "user", "content": text}
                ],
                temperature=0.1
            )
            
            result = response.choices[0].message.content.strip()
            
            # Try to parse as JSON
            try:
                function_call = json.loads(result)
                if function_call.get("function_name") and function_call.get("function_name") != "none":
                    await self._execute_function(function_call, session, room_id, text)
                    return True
            except json.JSONDecodeError:
                # If not JSON, check if it's a "none" response
                if result.lower() == "none":
                    return False
                    
        except Exception as e:
            print(f"Error parsing function: {e}")
            return False
        
        return False
    
    async def _execute_function(self, function_call: dict, session, room_id: str, original_command: str):
        """Execute the parsed function and store in memory"""
        function_name = function_call.get("function_name")
        parameters = function_call.get("parameters", {})
        
        if function_name in self.available_functions:
            try:
                # Create a mock context for the function
                class MockContext:
                    pass
                
                mock_context = MockContext()
                
                # Execute the function with mock context
                result = await self.available_functions[function_name](mock_context, **parameters)
                
                print(f"Function {function_name} executed: {result}")
                
                # Store command execution in memory
                self.memory.store_command_execution(
                    command=original_command,
                    function_name=function_name,
                    parameters=parameters,
                    result=result,
                    room_id=room_id
                )
                
                # Increment usage metric
                self.memory.increment_usage_metric(f"function_{function_name}")
                
                # Send result back to assistant
                await session.generate_reply(instructions=f"The function {function_name} was executed with result: {result}")
                
            except Exception as e:
                error_msg = f"Error executing {function_name}: {str(e)}"
                print(f"{error_msg}")
                await session.generate_reply(instructions=f"There was an error: {error_msg}")
        else:
            print(f"Unknown function: {function_name}")

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
# Memory Command Handler
# --------------------------------------------- 
async def handle_memory_commands(transcription: str, session, room_id: str = None) -> bool:
    """Handle special memory-related commands"""
    text = transcription.lower()
    
    # Remember something
    if text.startswith("remember that") or text.startswith("remember this"):
        memory_text = text.replace("remember that", "").replace("remember this", "").strip()
        memory.set_context("user_note", memory_text, expiry_minutes=1440, room_id=room_id)  # 24 hours
        await session.generate_reply(instructions=f"I'll remember that: {memory_text}")
        return True
    
    # Recall something
    elif "what do you remember" in text or "what did i tell you to remember" in text:
        user_note = memory.get_context("user_note", room_id)
        if user_note:
            await session.generate_reply(instructions=f"You told me to remember: {user_note}")
        else:
            await session.generate_reply(instructions="I don't have any specific notes to remember right now.")
        return True
    
    # Clear memory
    elif "forget everything" in text or "clear memory" in text:
        memory.clear_context(room_id=room_id)
        await session.generate_reply(instructions="I've cleared my memory context.")
        return True
    
    # Memory status
    elif any(phrase in text for phrase in [
        "memory status",
        "what is your memory status",
        "how is your memory",
        "what's your memory"
    ]):

        status = memory.get_memory_status()
        await session.generate_reply(instructions=f"Memory status: {status}")
        return True
    
    # Set preference
    elif text.startswith("set preference") or text.startswith("i prefer"):
        # Simple preference setting - you can expand this
        if "voice" in text:
            if "aoede" in text:
                memory.set_user_preference("voice", "Aoede", room_id)
                await session.generate_reply(instructions="I've set your voice preference to Aoede.")
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
            await session.generate_reply(instructions=commands_text)
        else:
            await session.generate_reply(instructions="No recent commands to show.")
        return True
    
    return False

# --------------------------------------------- 
# Enhanced Wake Word Detection with Memory
# --------------------------------------------- 
async def listen_for_wake_word_and_respond(session, room_id: str = None):
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
    
    # Initialize STT handler and function parser with memory
    stt_handler = STTHandler()
    function_parser = FunctionParser(memory)
    
    print("Wake word listener running. Say 'Jarvis' anytime to trigger the assistant.")
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
                max_timeout = 50  # 5 seconds timeout
                
                while not speech_detected and timeout_counter < max_timeout:
                    transcription = await stt_handler.get_transcription()
                    if transcription:
                        print(f"🎤 Transcribed: '{transcription}'")
                        
                        # Check for special memory commands
                        if await handle_memory_commands(transcription, session, room_id):
                            speech_detected = True
                            continue
                        
                        # Parse for function calls with memory context
                        function_executed = await function_parser.parse_and_execute(
                            transcription, session, room_id
                        )
                        
                        # Store the conversation
                        memory.store_conversation(
                            user_input=transcription,
                            assistant_response="[Processing...]",
                            room_id=room_id
                        )
                        
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
                    print("No speech detected within timeout period")
                    await session.generate_reply(instructions="I didn't hear anything, sir. How may I assist you?")
            
            await asyncio.sleep(0.01)  # Small delay to prevent busy waiting
    
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
    """Main entrypoint for the LiveKit agent"""
    print("Starting Jarvis with Redis Memory System...")
    print(f"Connected to room: {ctx.room.name}")
    print(f"Memory system status: {memory.get_memory_status()}")
    
    # Get room ID for session management
    room_id = ctx.room.name
    
    # Initialize agent with memory
    agent = JarvisAgent(memory)
    
    # Start the agent session
    session = AgentSession()
    
    await session.start(
        room=ctx.room,
        agent=agent,
        room_input_options=RoomInputOptions(
            video_enabled=True,
            noise_cancellation=noise_cancellation.BVC(),
        ),
    )
    
    print("LiveKit session started and connected to room.")
    
    # Start wake word listening in background
    asyncio.create_task(listen_for_wake_word_and_respond(session, room_id))
    
    # Keep the connection alive
    await ctx.connect()

# --------------------------------------------- 
# Main Entry Point
# --------------------------------------------- 
if __name__ == "__main__":
    print("Starting Jarvis with Redis Memory System...")
    print("Memory commands available:")
    print("- 'Remember that [something]' - Store a note")
    print("- 'What do you remember' - Recall stored notes")
    print("- 'Forget everything' - Clear memory")
    print("- 'Memory status' - Check memory system status")
    print("- 'Set preference voice aoede' - Set voice preference")
    print("- 'Show recent commands' - Display recent command history")
    
    # Run the LiveKit CLI
    agents.cli.run_app(agents.WorkerOptions(entrypoint_fnc=entrypoint))