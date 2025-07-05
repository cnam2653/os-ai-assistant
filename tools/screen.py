import logging
from livekit.agents import function_tool, RunContext
import pyautogui
import os
from datetime import datetime

@function_tool()
async def take_screenshot(
    context: RunContext,  # type: ignore
    filename: str = None) -> str:
    """
    Take a screenshot of the current screen.
    
    Args:
        filename: Optional filename to save the screenshot (default: timestamp-based name)
    """
    try:
        # Generate filename if not provided
        if filename is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"screenshot_{timestamp}.png"
        
        # Ensure filename has .png extension
        if not filename.lower().endswith('.png'):
            filename += '.png'
        
        # Take screenshot
        screenshot = pyautogui.screenshot()
        
        # Save screenshot
        screenshot.save(filename)
        
        # Get full path
        full_path = os.path.abspath(filename)
        
        logging.info(f"Screenshot saved as: {full_path}")
        return f"Screenshot saved as: {full_path}"
        
    except Exception as e:
        logging.error(f"Error taking screenshot: {e}")
        return f"An error occurred while taking screenshot: {str(e)}"

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