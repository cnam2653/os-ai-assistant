import logging
from livekit.agents import function_tool, RunContext
import pyautogui
import os
from datetime import datetime
import base64
from io import BytesIO

@function_tool()
async def take_screenshot(
    context: RunContext,  # type: ignore
    filename: str = None) -> str:
    """
    Take a screenshot of the current screen and save it to the Screenshots folder.
    
    Args:
        filename: Optional filename to save the screenshot (default: timestamp-based name)
    """
    try:
        logging.info("Screenshot function called")
        
        # Set the fixed directory
        screenshots_dir = r"C:\Users\Chris\OneDrive\Pictures\Screenshots"
        logging.info(f"Target directory: {screenshots_dir}")
        
        # Check if directory exists first
        if os.path.exists(screenshots_dir):
            logging.info("Directory exists")
        else:
            logging.info("Directory does not exist, creating...")
        
        # Create directory if it doesn't exist
        os.makedirs(screenshots_dir, exist_ok=True)
        logging.info("Directory created/verified")
        
        # Check directory permissions
        if os.access(screenshots_dir, os.W_OK):
            logging.info("Directory is writable")
        else:
            logging.error("Directory is not writable!")
            return f"Error: Cannot write to directory {screenshots_dir}"
        
        # Generate filename if not provided
        if filename is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"screenshot_{timestamp}.png"
        
        # Ensure filename has .png extension
        if not filename.lower().endswith('.png'):
            filename += '.png'
        
        # Create full path
        full_path = os.path.join(screenshots_dir, filename)
        logging.info(f"Full path: {full_path}")
        
        # Check current working directory
        current_dir = os.getcwd()
        logging.info(f"Current working directory: {current_dir}")
        
        # Take screenshot
        logging.info("Taking screenshot...")
        screenshot = pyautogui.screenshot()
        logging.info(f"Screenshot captured - Size: {screenshot.size}")
        
        # Try saving to alternative location first for testing
        temp_path = os.path.join(current_dir, filename)
        logging.info(f"Saving test screenshot to: {temp_path}")
        screenshot.save(temp_path)
        
        if os.path.exists(temp_path):
            logging.info("Test screenshot saved successfully in current directory")
            
            # Now try the target location
            screenshot.save(full_path)
            logging.info(f"Screenshot saved to target location: {full_path}")
            
            # Verify file exists in target location
            if os.path.exists(full_path):
                file_size = os.path.getsize(full_path)
                logging.info(f"File verified in target location - Size: {file_size} bytes")
                # Clean up test file
                try:
                    os.remove(temp_path)
                    logging.info("Test file cleaned up")
                except:
                    pass
                return f"Screenshot successfully saved to: {full_path} (Size: {file_size} bytes)"
            else:
                logging.error("File was not created in target location")
                return f"Error: Screenshot saved to {temp_path} but failed to save to target location {full_path}"
        else:
            logging.error("Test screenshot failed")
            return "Error: Could not save screenshot anywhere"
    
    except Exception as e:
        logging.error(f"Error taking screenshot: {e}")
        import traceback
        logging.error(f"Full traceback: {traceback.format_exc()}")
        return f"An error occurred while taking screenshot: {str(e)}"

@function_tool()
async def read_screen(
    context: RunContext,  # type: ignore
) -> str:
    """
    Take a screenshot and describe what's currently on the screen.
    """
    try:
        logging.info("Screen reading function called")
        import os
        import openai
        from dotenv import load_dotenv

        load_dotenv()  # loads .env if needed
        if not openai.api_key:
            openai.api_key = os.getenv("OPENAI_API_KEY")
        # Take screenshot
        logging.info("Taking screenshot for screen reading...")
        screenshot = pyautogui.screenshot()
        logging.info(f"Screenshot captured - Size: {screenshot.size}")
        
        # Convert screenshot to base64 for AI analysis
        buffer = BytesIO()
        screenshot.save(buffer, format='PNG')
        img_base64 = base64.b64encode(buffer.getvalue()).decode()
        
        # Try using OpenAI GPT-4 Vision
        try:
            
            response = openai.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "text",
                                "text": "Describe what you see on this screen. Include details about any applications, documents, videos, websites, or other content that's visible. Be specific about what's displayed and what the user might be working on."
                            },
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:image/png;base64,{img_base64}"
                                }
                            }
                        ]
                    }
                ],
                max_tokens=500
            )
            
            description = response.choices[0].message.content
            logging.info(f"Screen reading completed successfully")
            return f"Here's what I can see on your screen: {description}"
            
        except ImportError:
            logging.error("OpenAI library not installed")
            return "Error: OpenAI library not installed. Please install it with: pip install openai"
        except Exception as api_error:
            logging.error(f"API error: {api_error}")
            
            # Fallback: Basic screen analysis without AI
            try:
                import psutil
                import win32gui
                import win32process
                
                def get_active_window():
                    try:
                        hwnd = win32gui.GetForegroundWindow()
                        if hwnd:
                            window_text = win32gui.GetWindowText(hwnd)
                            _, pid = win32process.GetWindowThreadProcessId(hwnd)
                            try:
                                process = psutil.Process(pid)
                                process_name = process.name()
                                return f"Active window: '{window_text}' (Application: {process_name})"
                            except:
                                return f"Active window: '{window_text}'"
                        return "No active window detected"
                    except:
                        return "Could not detect active window"
                
                # Get basic screen info
                screen_width, screen_height = pyautogui.size()
                active_window = get_active_window()
                
                return f"Screen resolution: {screen_width}x{screen_height}. {active_window}. Note: For detailed screen content description, please configure OpenAI API key for GPT-4 Vision."
                
            except ImportError:
                screen_width, screen_height = pyautogui.size()
                return f"Screen resolution: {screen_width}x{screen_height}. For detailed screen reading, please install required libraries: pip install openai pywin32 psutil"
    
    except Exception as e:
        logging.error(f"Error reading screen: {e}")
        import traceback
        logging.error(f"Full traceback: {traceback.format_exc()}")
        return f"An error occurred while reading screen: {str(e)}"
    
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