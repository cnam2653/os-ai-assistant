import logging
from livekit.agents import function_tool, RunContext
import requests
from langchain_community.tools import DuckDuckGoSearchRun
import os
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Optional
import subprocess
import psutil
import pyautogui
import time
from datetime import datetime  # Added missing import

# Audio control imports
try:
    from pycaw.pycaw import AudioUtilities, AudioEndpointVolume
    from comtypes import CLSCTX_ALL
    from ctypes import cast, POINTER
    from comtypes.interfaces import IUnknown
    AUDIO_AVAILABLE = True
except ImportError:
    print("Warning: Audio control libraries not available. Install pycaw and comtypes for audio functionality.")
    AUDIO_AVAILABLE = False

# Configure PyAutoGUI
pyautogui.FAILSAFE = True  # Move mouse to top-left corner to abort
pyautogui.PAUSE = 0.1  # Small pause between actions

@function_tool()
async def get_weather(
    context: RunContext,  # type: ignore
    city: str) -> str:
    """
    Get the current weather for a given city.
    """
    try:
        response = requests.get(
            f"https://wttr.in/{city}?format=3")
        if response.status_code == 200:
            logging.info(f"Weather for {city}: {response.text.strip()}")
            return response.text.strip()
        else:
            logging.error(f"Failed to get weather for {city}: {response.status_code}")
            return f"Could not retrieve weather for {city}."
    except Exception as e:
        logging.error(f"Error retrieving weather for {city}: {e}")
        return f"An error occurred while retrieving weather for {city}."

@function_tool()
async def search_web(
    context: RunContext,  # type: ignore
    query: str) -> str:
    """
    Search the web using DuckDuckGo.
    """
    try:
        results = DuckDuckGoSearchRun().run(tool_input=query)
        logging.info(f"Search results for '{query}': {results}")
        return results
    except Exception as e:
        logging.error(f"Error searching the web for '{query}': {e}")
        return f"An error occurred while searching the web for '{query}'."

@function_tool()
async def send_email(
    context: RunContext,  # type: ignore
    to_email: str,
    subject: str,
    message: str,
    cc_email: Optional[str] = None
) -> str:
    """
    Send an email through Gmail.
    
    Args:
        to_email: Recipient email address
        subject: Email subject line
        message: Email body content
        cc_email: Optional CC email address
    """
    try:
        # Gmail SMTP configuration
        smtp_server = "smtp.gmail.com"
        smtp_port = 587
        
        # Get credentials from environment variables
        gmail_user = os.getenv("GMAIL_USER")
        gmail_password = os.getenv("GMAIL_APP_PASSWORD")  # Use App Password, not regular password
        
        if not gmail_user or not gmail_password:
            logging.error("Gmail credentials not found in environment variables")
            return "Email sending failed: Gmail credentials not configured."
        
        # Create message
        msg = MIMEMultipart()
        msg['From'] = gmail_user
        msg['To'] = to_email
        msg['Subject'] = subject
        
        # Add CC if provided
        recipients = [to_email]
        if cc_email:
            msg['Cc'] = cc_email
            recipients.append(cc_email)
        
        # Attach message body
        msg.attach(MIMEText(message, 'plain'))
        
        # Connect to Gmail SMTP server
        server = smtplib.SMTP(smtp_server, smtp_port)
        server.starttls()  # Enable TLS encryption
        server.login(gmail_user, gmail_password)
        
        # Send email
        text = msg.as_string()
        server.sendmail(gmail_user, recipients, text)
        server.quit()
        
        logging.info(f"Email sent successfully to {to_email}")
        return f"Email sent successfully to {to_email}"
        
    except smtplib.SMTPAuthenticationError:
        logging.error("Gmail authentication failed")
        return "Email sending failed: Authentication error. Please check your Gmail credentials."
    except smtplib.SMTPException as e:
        logging.error(f"SMTP error occurred: {e}")
        return f"Email sending failed: SMTP error - {str(e)}"
    except Exception as e:
        logging.error(f"Error sending email: {e}")
        return f"An error occurred while sending email: {str(e)}"

@function_tool()
async def open_file(
    context: RunContext,  # type: ignore
    file_path: str) -> str:
    """
    Open a file or folder using the default Windows application.
    
    Args:
        file_path: Full path to the file or folder to open
    """
    try:
        # Normalize the path and handle Windows path formats
        file_path = os.path.normpath(file_path)
        
        # Check if path exists
        if not os.path.exists(file_path):
            logging.error(f"File or folder not found: {file_path}")
            return f"File or folder not found: {file_path}"
        
        # Open file/folder with default Windows application
        os.startfile(file_path)
        
        file_type = "folder" if os.path.isdir(file_path) else "file"
        logging.info(f"Successfully opened {file_type}: {file_path}")
        return f"Successfully opened {file_type}: {os.path.basename(file_path)}"
        
    except Exception as e:
        logging.error(f"Error opening file {file_path}: {e}")
        return f"An error occurred while opening {file_path}: {str(e)}"

@function_tool()
async def open_application(
    context: RunContext,  # type: ignore
    app_name: str) -> str:
    """
    Open an application by name on Windows using direct paths for faster execution.
    
    Args:
        app_name: Name of the application to open
    """
    
    # Direct path mappings 
    app_mappings = {
        # Browsers 
        "chrome": [r"C:\Program Files\Google\Chrome\Application\chrome.exe"],
        "google chrome": [r"C:\Program Files\Google\Chrome\Application\chrome.exe"],
        
        # Communication 
        "discord": [r"C:\Users\Chris\AppData\Local\Discord\app-1.0.9198\Discord.exe"],
        
        # Gaming - Update these paths
        "steam": [r"C:\Program Files (x86)\Steam\Steam.exe"],
        "valorant": [r"C:\ProgramData\Microsoft\Windows\Start Menu\Programs\Riot Games\VALORANT.lnk"],
        
        # Media - Update these paths
        "spotify": [r"C:\Users\Chris\AppData\Roaming\Spotify\Spotify.exe"],
        "medal": [r"C:\Users\Chris\AppData\Local\Medal\app-4.2746.0\Medal.exe"],
        
        # Development - Update with your VS Code path
        "vscode": [r"C:\Users\Chris\AppData\Roaming\Microsoft\Windows\Start Menu\Programs\Visual Studio Code\Visual Studio Code.lnk"],
        "visual studio code": [r"C:\Users\Chris\AppData\Roaming\Microsoft\Windows\Start Menu\Programs\Visual Studio Code\Visual Studio Code.lnk"],
        
        # System apps 
        "powershell": [r"C:\Windows\System32\WindowsPowerShell\v1.0\powershell.exe"],
        "cmd": [r"C:\Windows\System32\cmd.exe"],
        "command prompt": [r"C:\Windows\System32\cmd.exe"],
        "task manager": [r"C:\Windows\System32\taskmgr.exe"],
        "settings": ["ms-settings:"],  # This one uses protocol handler
        "notepad": [r"C:\Windows\System32\notepad.exe"],
        "paint": [r"C:\Windows\System32\mspaint.exe"],
        "explorer": [r"C:\Windows\explorer.exe"],
        "file explorer": [r"C:\Windows\explorer.exe"],
        
        # Special cases
        "google meet": [r"C:\Program Files\Google\Chrome\Application\chrome.exe", "https://meet.google.com"],
    }
    
    app_name_lower = app_name.lower()
    
    if app_name_lower not in app_mappings:
        logging.warning(f"Application '{app_name}' is not in the allowed list")
        return f"Sorry, I can only open these applications: {', '.join(app_mappings.keys())}"
    
    try:
        # Check if application is already running
        for proc in psutil.process_iter(['pid', 'name']):
            try:
                if app_name_lower in proc.info['name'].lower():
                    logging.info(f"{app_name} is already running (PID: {proc.info['pid']})")
                    return f"{app_name} is already running."
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue
        
        # Get the path(s) for the application
        paths = app_mappings[app_name_lower]
        
        # Special handling for Google Meet
        if app_name_lower == "google meet":
            chrome_path = paths[0]
            url = paths[1]
            if os.path.exists(chrome_path):
                subprocess.Popen([chrome_path, url])
                logging.info(f"Successfully opened Google Meet in Chrome")
                return f"Successfully opened Google Meet in Chrome"
            else:
                return f"Chrome not found at {chrome_path}"
        
        # Try each path until one works
        for path in paths:
            try:
                logging.debug(f"Trying path: {path}")

                if path.startswith("ms-settings:"):
                    subprocess.run(["start", path], shell=True, check=True)
                    logging.info(f"Successfully opened {app_name}")
                    return f"Successfully opened {app_name}"

                if "--" in path:
                    exe_path, args_str = path.split(" --", 1)
                    exe_path = exe_path.strip()
                    args = ["--" + arg.strip() for arg in args_str.split("--") if arg.strip()]
                else:
                    exe_path = path
                    args = []

                logging.debug(f"Checking if executable exists: {exe_path}")
                if os.path.exists(exe_path):
                    logging.debug(f"Executable found: {exe_path}")
                    if args:
                        subprocess.Popen([exe_path] + args)
                    else:
                        subprocess.Popen([exe_path])

                    logging.info(f"Successfully opened {app_name}")
                    return f"Successfully opened {app_name}"
                else:
                    logging.warning(f"Path does not exist or is invalid: {exe_path}")
                    continue

            except Exception as e:
                logging.error(f"Failed to open {path}: {e}")
                continue

        return f"Could not find or open {app_name}"

    except Exception as e:
        logging.error(f"Error opening {app_name}: {e}")
        return f"An error occurred while trying to open {app_name}: {str(e)}"

@function_tool()
async def find_app_paths(
    context: RunContext,  # type: ignore
    app_name: str) -> str:
    """
    Helper function to find the actual installation paths for applications.
    Use this to discover the correct paths for your system.
    """
    try:
        found_paths = []
        
        # Common installation directories
        search_paths = [
            os.path.expandvars(r"%ProgramFiles%"),
            os.path.expandvars(r"%ProgramFiles(x86)%"),
            os.path.expandvars(r"%LocalAppData%\Programs"),
            os.path.expandvars(r"%AppData%\Local"),
            os.path.expandvars(r"%AppData%\Roaming"),
        ]
        
        app_name_lower = app_name.lower()
        
        for base_path in search_paths:
            if os.path.exists(base_path):
                for root, dirs, files in os.walk(base_path):
                    # Look for executable files
                    for file in files:
                        if file.lower().endswith('.exe') and app_name_lower in file.lower():
                            full_path = os.path.join(root, file)
                            found_paths.append(full_path)
                    
                    # Also look for folders with the app name
                    for dir_name in dirs:
                        if app_name_lower in dir_name.lower():
                            # Look for exe files in this directory
                            app_dir = os.path.join(root, dir_name)
                            try:
                                for file in os.listdir(app_dir):
                                    if file.lower().endswith('.exe'):
                                        full_path = os.path.join(app_dir, file)
                                        found_paths.append(full_path)
                            except (PermissionError, OSError):
                                continue
                    
                    # Limit search depth to avoid taking too long
                    if len(root.split(os.sep)) - len(base_path.split(os.sep)) > 3:
                        dirs[:] = []
        
        if found_paths:
            # Remove duplicates and limit results
            unique_paths = list(dict.fromkeys(found_paths))[:10]
            return f"Found {app_name} at these locations:\n" + "\n".join(unique_paths)
        else:
            return f"Could not find {app_name} in common installation directories."
            
    except Exception as e:
        logging.error(f"Error finding {app_name}: {e}")
        return f"An error occurred while searching for {app_name}: {str(e)}"

@function_tool()
async def close_application(
    context: RunContext,  # type: ignore
    app_name: str) -> str:
    """
    Close an application by name on Windows with better process targeting.
    
    Args:
        app_name: Name of the application to close (e.g., "steam", "chrome", "notepad")
    """
    app_name_lower = app_name.lower()
    closed_processes = []
    
    # More specific process name mappings for better targeting
    process_mappings = {
        "chrome": ["chrome.exe"],
        "google chrome": ["chrome.exe"],
        "firefox": ["firefox.exe"],
        "edge": ["msedge.exe"],
        "microsoft edge": ["msedge.exe"],
        "discord": ["Discord.exe"],
        "steam": ["steam.exe"],
        "valorant": ["VALORANT.exe", "RiotClientServices.exe"],
        "spotify": ["Spotify.exe"],
        "medal": ["Medal.exe"],
        "vscode": ["Code.exe"],
        "visual studio code": ["Code.exe"],
        "powershell": ["powershell.exe"],
        "cmd": ["cmd.exe"],
        "command prompt": ["cmd.exe"],
        "task manager": ["taskmgr.exe"],
        "calculator": ["calc.exe"],
        "notepad": ["notepad.exe"],
        "paint": ["mspaint.exe"],
        "explorer": ["explorer.exe"],
        "file explorer": ["explorer.exe"],
    }
    
    try:
        # Get the specific process names to look for
        if app_name_lower in process_mappings:
            target_processes = process_mappings[app_name_lower]
        else:
            # Fallback to generic matching
            target_processes = [f"{app_name_lower}.exe"]
        
        # Find and terminate processes matching the specific process names
        for proc in psutil.process_iter(['pid', 'name']):
            try:
                proc_name = proc.info['name'].lower()
                if any(target.lower() == proc_name for target in target_processes):
                    proc.terminate()
                    closed_processes.append(f"{proc.info['name']} (PID: {proc.info['pid']})")
                    logging.info(f"Terminated {proc.info['name']} (PID: {proc.info['pid']})")
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue
        
        if closed_processes:
            return f"Successfully closed {app_name}: {', '.join(closed_processes)}"
        else:
            return f"{app_name} is not currently running."
            
    except Exception as e:
        logging.error(f"Error closing {app_name}: {e}")
        return f"An error occurred while trying to close {app_name}: {str(e)}"

@function_tool()
async def run_command(
    context: RunContext,  # type: ignore
    command: str) -> str:
    """
    Run a Windows command line command.
    
    Args:
        command: The command to execute
    """
    try:
        # Run the command and capture output
        result = subprocess.run(
            command,
            shell=True,
            capture_output=True,
            text=True,
            timeout=30  # 30 second timeout
        )
        
        output = result.stdout.strip()
        error = result.stderr.strip()
        
        if result.returncode == 0:
            logging.info(f"Command '{command}' executed successfully")
            return f"Command executed successfully:\n{output}" if output else "Command executed successfully (no output)"
        else:
            logging.error(f"Command '{command}' failed with return code {result.returncode}")
            return f"Command failed with return code {result.returncode}:\n{error}" if error else f"Command failed with return code {result.returncode}"
            
    except subprocess.TimeoutExpired:
        logging.error(f"Command '{command}' timed out")
        return f"Command timed out after 30 seconds"
    except Exception as e:
        logging.error(f"Error running command '{command}': {e}")
        return f"An error occurred while running the command: {str(e)}"

# =============================================================================
# FUNCTIONS FOR MOUSE, KEYBOARD, AND AUDIO CONTROL
# =============================================================================

@function_tool()
async def move_cursor(
    context: RunContext,  # type: ignore
    direction: str,
    distance: int = 100) -> str:
    """
    Move the cursor in a specified direction.
    
    Args:
        direction: Direction to move ('up', 'down', 'left', 'right', 'center')
        distance: Number of pixels to move (default: 100)
    """
    try:
        current_x, current_y = pyautogui.position()
        
        if direction.lower() == "up":
            pyautogui.moveTo(current_x, current_y - distance)
        elif direction.lower() == "down":
            pyautogui.moveTo(current_x, current_y + distance)
        elif direction.lower() == "left":
            pyautogui.moveTo(current_x - distance, current_y)
        elif direction.lower() == "right":
            pyautogui.moveTo(current_x + distance, current_y)
        elif direction.lower() == "center":
            screen_width, screen_height = pyautogui.size()
            pyautogui.moveTo(screen_width // 2, screen_height // 2)
        else:
            return f"Invalid direction: {direction}. Use 'up', 'down', 'left', 'right', or 'center'."
        
        new_x, new_y = pyautogui.position()
        logging.info(f"Moved cursor {direction} by {distance} pixels to ({new_x}, {new_y})")
        return f"Moved cursor {direction} to position ({new_x}, {new_y})"
        
    except Exception as e:
        logging.error(f"Error moving cursor {direction}: {e}")
        return f"An error occurred while moving cursor {direction}: {str(e)}"

@function_tool()
async def click_mouse(
    context: RunContext,  # type: ignore
    button: str = "left",
    clicks: int = 1) -> str:
    """
    Click the mouse button.
    
    Args:
        button: Mouse button to click ('left', 'right', 'middle')
        clicks: Number of clicks (default: 1)
    """
    try:
        if button.lower() not in ["left", "right", "middle"]:
            return f"Invalid button: {button}. Use 'left', 'right', or 'middle'."
        
        current_x, current_y = pyautogui.position()
        
        if button.lower() == "left":
            pyautogui.click(clicks=clicks)
        elif button.lower() == "right":
            pyautogui.rightClick()
        elif button.lower() == "middle":
            pyautogui.middleClick()
        
        logging.info(f"Clicked {button} mouse button {clicks} times at ({current_x}, {current_y})")
        return f"Clicked {button} mouse button {clicks} times at ({current_x}, {current_y})"
        
    except Exception as e:
        logging.error(f"Error clicking {button} mouse button: {e}")
        return f"An error occurred while clicking {button} mouse button: {str(e)}"

@function_tool()
async def scroll_mouse(
    context: RunContext,  # type: ignore
    direction: str,
    amount: int = 3) -> str:
    """
    Scroll the mouse wheel.
    
    Args:
        direction: Direction to scroll ('up', 'down')
        amount: Number of scroll steps (default: 3)
    """
    try:
        if direction.lower() == "up":
            pyautogui.scroll(amount)
        elif direction.lower() == "down":
            pyautogui.scroll(-amount)
        else:
            return f"Invalid direction: {direction}. Use 'up' or 'down'."
        
        logging.info(f"Scrolled {direction} by {amount} steps")
        return f"Scrolled {direction} by {amount} steps"
        
    except Exception as e:
        logging.error(f"Error scrolling {direction}: {e}")
        return f"An error occurred while scrolling {direction}: {str(e)}"

@function_tool()
async def type_text(
    context: RunContext,  # type: ignore
    text: str,
    interval: float = 0.05) -> str:
    """
    Type text using the keyboard.
    
    Args:
        text: Text to type
        interval: Interval between keystrokes in seconds (default: 0.05)
    """
    try:
        pyautogui.typewrite(text, interval=interval)
        logging.info(f"Typed text: '{text}'")
        return f"Successfully typed: '{text}'"
        
    except Exception as e:
        logging.error(f"Error typing text '{text}': {e}")
        return f"An error occurred while typing text: {str(e)}"

@function_tool()
async def press_key(
    context: RunContext,  # type: ignore
    key: str,
    presses: int = 1) -> str:
    """
    Press a key or key combination.
    
    Args:
        key: Key to press (e.g., 'enter', 'tab', 'ctrl+c', 'alt+tab')
        presses: Number of times to press the key (default: 1)
    """
    try:
        # Handle key combinations (e.g., 'ctrl+c')
        if '+' in key:
            keys = key.split('+')
            pyautogui.hotkey(*keys)
            logging.info(f"Pressed key combination: {key}")
            return f"Successfully pressed key combination: {key}"
        else:
            # Single key press
            for _ in range(presses):
                pyautogui.press(key)
                if presses > 1:
                    time.sleep(0.1)  # Small delay between presses
            
            logging.info(f"Pressed key '{key}' {presses} times")
            return f"Successfully pressed key '{key}' {presses} times"
        
    except Exception as e:
        logging.error(f"Error pressing key '{key}': {e}")
        return f"An error occurred while pressing key '{key}': {str(e)}"

@function_tool()
async def adjust_volume(
    context: RunContext,  # type: ignore
    action: str,
    amount: int = 10) -> str:
    """
    Adjust the system volume.
    
    Args:
        action: Action to perform ('up', 'down', 'mute', 'unmute', 'set')
        amount: Amount to change volume by (0-100) or set to (default: 10)
    """
    if not AUDIO_AVAILABLE:
        return "Audio control not available. Please install pycaw and comtypes libraries."
    
    try:
        # Get the default audio device
        devices = AudioUtilities.GetSpeakers()
        interface = devices.Activate(AudioEndpointVolume._iid_, CLSCTX_ALL, None)
        volume = cast(interface, POINTER(AudioEndpointVolume))
        
        current_volume = volume.GetMasterScalarVolume()
        current_volume_percent = int(current_volume * 100)
        
        if action.lower() == "up":
            new_volume = min(1.0, current_volume + (amount / 100.0))
            volume.SetMasterScalarVolume(new_volume, None)
            new_volume_percent = int(new_volume * 100)
            logging.info(f"Volume increased from {current_volume_percent}% to {new_volume_percent}%")
            return f"Volume increased from {current_volume_percent}% to {new_volume_percent}%"
            
        elif action.lower() == "down":
            new_volume = max(0.0, current_volume - (amount / 100.0))
            volume.SetMasterScalarVolume(new_volume, None)
            new_volume_percent = int(new_volume * 100)
            logging.info(f"Volume decreased from {current_volume_percent}% to {new_volume_percent}%")
            return f"Volume decreased from {current_volume_percent}% to {new_volume_percent}%"
            
        elif action.lower() == "mute":
            volume.SetMute(1, None)
            logging.info("Volume muted")
            return "Volume muted"
            
        elif action.lower() == "unmute":
            volume.SetMute(0, None)
            logging.info("Volume unmuted")
            return "Volume unmuted"
            
        elif action.lower() == "set":
            if 0 <= amount <= 100:
                new_volume = amount / 100.0
                volume.SetMasterScalarVolume(new_volume, None)
                logging.info(f"Volume set to {amount}%")
                return f"Volume set to {amount}%"
            else:
                return "Volume must be between 0 and 100"
                
        else:
            return f"Invalid action: {action}. Use 'up', 'down', 'mute', 'unmute', or 'set'."
            
    except Exception as e:
        logging.error(f"Error adjusting volume: {e}")
        return f"An error occurred while adjusting volume: {str(e)}"

@function_tool()
async def take_screenshot(
    context: RunContext,  # type: ignore
    filename: Optional[str] = None) -> str:
    """
    Take a screenshot and save it to a file.
    
    Args:
        filename: Optional filename to save the screenshot (default: auto-generated)
    """
    try:
        if filename is None:
            # Generate filename with timestamp
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"screenshot_{timestamp}.png"
        
        # Ensure filename ends with .png
        if not filename.lower().endswith('.png'):
            filename += '.png'
        
        # Take screenshot
        screenshot = pyautogui.screenshot()
        
        # Save to current directory or specified path
        if not os.path.dirname(filename):
            filename = os.path.join(os.getcwd(), filename)
        
        screenshot.save(filename)
        
        logging.info(f"Screenshot saved as {filename}")
        return f"Screenshot saved as {filename}"
        
    except Exception as e:
        logging.error(f"Error taking screenshot: {e}")
        return f"An error occurred while taking screenshot: {str(e)}"

@function_tool()
async def get_cursor_position(
    context: RunContext  # type: ignore
) -> str:
    """
    Get the current cursor position.
    """
    try:
        x, y = pyautogui.position()
        logging.info(f"Current cursor position: ({x}, {y})")
        return f"Current cursor position: ({x}, {y})"
        
    except Exception as e:
        logging.error(f"Error getting cursor position: {e}")
        return f"An error occurred while getting cursor position: {str(e)}"

@function_tool()
async def get_screen_size(
    context: RunContext  # type: ignore
) -> str:
    """
    Get the screen size.
    """
    try:
        width, height = pyautogui.size()
        logging.info(f"Screen size: {width}x{height}")
        return f"Screen size: {width}x{height}"
        
    except Exception as e:
        logging.error(f"Error getting screen size: {e}")
        return f"An error occurred while getting screen size: {str(e)}"