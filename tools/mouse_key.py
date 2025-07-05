import logging
from livekit.agents import function_tool, RunContext
import pyautogui
import time

# Configure PyAutoGUI
pyautogui.FAILSAFE = True  # Move mouse to top-left corner to abort
pyautogui.PAUSE = 0.1  # Small pause between actions

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