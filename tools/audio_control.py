import logging
from livekit.agents import function_tool, RunContext
import pyautogui
import time

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

@function_tool()
async def adjust_volume(
    context: RunContext,  # type: ignore
    action: str,
    amount: int = 5) -> str:
    """
    Adjust the system volume using Windows volume keys.
    
    Args:
        action: Action to perform ('up', 'down', 'mute', 'unmute')
        amount: Number of volume steps for up/down (default: 5)
    """
    try:
        if action.lower() == "up" or action.lower() == "increase":
            for i in range(amount):
                pyautogui.press('volumeup')
                time.sleep(0.1)  # Increased delay
                logging.info(f"Volume step {i+1}/{amount}")
            logging.info(f"Volume increased by {amount} steps")
            return f"Volume increased by {amount} steps"
            
        elif action.lower() == "down" or action.lower() == "decrease":
            for i in range(amount):
                pyautogui.press('volumedown')
                time.sleep(0.1)  # Increased delay
                logging.info(f"Volume step {i+1}/{amount}")
            logging.info(f"Volume decreased by {amount} steps")
            return f"Volume decreased by {amount} steps"
            
        elif action.lower() in ["mute", "unmute"]:
            pyautogui.press('volumemute')
            logging.info("Volume mute toggled")
            return "Volume mute toggled"
            
        else:
            return f"Invalid action: {action}. Use 'up', 'down', 'mute', or 'unmute'."
            
    except Exception as e:
        logging.error(f"Error adjusting volume: {e}")
        return f"An error occurred while adjusting volume: {str(e)}"