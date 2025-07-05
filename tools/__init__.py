from .audio_control import adjust_volume
from .mouse_key import move_cursor, click_mouse, scroll_mouse, type_text, press_key
from .screen import take_screenshot, get_screen_size
from .os_commands import open_file, run_command, close_application, send_email
from .web_utils import get_weather, search_web

__all__ = [
    "adjust_volume",
    "move_cursor", "click_mouse", "scroll_mouse", "type_text", "press_key",
    "take_screenshot", "get_cursor_position", "get_screen_size",
    "open_file", "run_command", "close_application",
    "get_weather", "search_web", "send_email"
]
