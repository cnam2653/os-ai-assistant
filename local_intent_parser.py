import os
import re
from typing import Dict, Any, Optional, Tuple
import joblib
import torch
from transformers import AutoTokenizer, AutoModelForSequenceClassification

class LocalIntentParser:
    def __init__(self, model_path: str = "./intent_model/"):
        """Initialize the local intent parser with trained model"""
        self.model_path = model_path
        self.model = None
        self.tokenizer = None
        self.label_encoder = None
        self.confidence_threshold = 0.15  # Minimum confidence for classification

        # Load model and components
        self._load_model()

        # All intents in your training set!
        self.intent_to_function = {
            'open_application': self._parse_open_application,
            'close_application': self._parse_close_application,
            'get_weather': self._parse_get_weather,
            'search_web': self._parse_search_web,
            'type_text': self._parse_type_text,
            'press_key': self._parse_press_key,
            'take_screenshot': self._parse_take_screenshot,
            'read_screen': self._parse_read_screen,
            'adjust_volume': self._parse_adjust_volume,
            'get_current_time': self._parse_get_current_time,
            'get_current_date': self._parse_get_current_date,
            'send_email': self._parse_send_email,
            'open_file': self._parse_open_file,
            'scroll_mouse': self._parse_scroll_mouse,
            'click_mouse': self._parse_click_mouse,
            'move_cursor': self._parse_move_cursor,
            'get_cursor_position': self._parse_get_cursor_position,
            'get_screen_size': self._parse_get_screen_size,
            'run_command': self._parse_run_command,
            'start_interview_session': self._parse_start_interview_session,
            'get_next_question': self._parse_get_next_question,
            'set_resume_path': self._parse_set_resume_path,
            'tell_about_yourself': self._parse_tell_about_yourself,
            'evaluate_interview': self._parse_evaluate_interview,
            'check_code_solution': self._parse_check_code_solution,
        }

    def _load_model(self):
        """Load trained model and tokenizer"""
        try:
            self.tokenizer = AutoTokenizer.from_pretrained(self.model_path)
            self.model = AutoModelForSequenceClassification.from_pretrained(self.model_path)
            self.model.eval()
            self.label_encoder = joblib.load(os.path.join(self.model_path, 'label_encoder.pkl'))
            print("✅ Local intent model loaded successfully!")
        except Exception as e:
            print(f"❌ Error loading model: {e}")
            raise

    def classify_intent(self, text: str) -> Tuple[str, float]:
        """Classify text and return intent with confidence score"""
        if not self.model or not self.tokenizer:
            raise RuntimeError("Model not loaded properly")
        inputs = self.tokenizer(text, return_tensors="pt", truncation=True, padding=True, max_length=512)
        with torch.no_grad():
            outputs = self.model(**inputs)
            predictions = torch.nn.functional.softmax(outputs.logits, dim=-1)
            confidence, predicted_class = torch.max(predictions, dim=-1)
        intent = self.label_encoder.inverse_transform([predicted_class.item()])[0]
        return intent, confidence.item()

    def parse_and_extract_function(self, text: str) -> Optional[Dict[str, Any]]:
        """Parse text and extract function call with parameters"""
        intent, confidence = self.classify_intent(text)
        print(f"Intent: {intent} (confidence: {confidence:.3f})")
        if confidence < self.confidence_threshold:
            print(f"Warning: Low confidence ({confidence:.3f}), skipping function execution")
            return None
        if intent in self.intent_to_function:
            try:
                function_call = self.intent_to_function[intent](text)
                if function_call:
                    function_call['confidence'] = confidence
                    return function_call
            except Exception as e:
                print(f"❌ Error parsing {intent}: {e}")
                return None
        return None

    # ================================
    # Intent-specific parameter parsing
    # ================================

    def _parse_open_application(self, text: str) -> Dict[str, Any]:
        app_patterns = {
            'chrome': ['chrome', 'google chrome', 'browser'],
            'notepad': ['notepad', 'text editor'],
            'calculator': ['calculator', 'calc'],
            'spotify': ['spotify', 'music'],
            'discord': ['discord'],
            'slack': ['slack'],
            'photoshop': ['photoshop', 'ps'],
            'excel': ['excel', 'spreadsheet'],
            'word': ['word', 'microsoft word'],
            'powerpoint': ['powerpoint', 'ppt'],
            'vscode': ['vscode', 'visual studio code', 'code'],
            'terminal': ['terminal', 'cmd', 'command prompt'],
            'outlook': ['outlook', 'email client'],
            'edge': ['edge', 'microsoft edge'],
            'steam': ['steam', 'steam client', 'team'],  # Add 'team' as common misrecognition
        }
        text_lower = text.lower()
        for app_name, patterns in app_patterns.items():
            if any(pattern in text_lower for pattern in patterns):
                return {'function_name': 'open_application', 'parameters': {'app_name': app_name}}
        patterns = [r'open (.+)', r'launch (.+)', r'start (.+)', r'run (.+)']
        for pattern in patterns:
            match = re.search(pattern, text_lower)
            if match:
                return {'function_name': 'open_application', 'parameters': {'app_name': match.group(1).strip()}}
        return {'function_name': 'open_application', 'parameters': {'app_name': 'unknown'}}

    def _parse_close_application(self, text: str) -> Dict[str, Any]:
        patterns = [r'close (.+)', r'quit (.+)', r'exit (.+)', r'shut down (.+)', r'stop (.+)']
        for pattern in patterns:
            match = re.search(pattern, text.lower())
            if match:
                return {'function_name': 'close_application', 'parameters': {'application_name': match.group(1).strip()}}
        return {'function_name': 'close_application', 'parameters': {'application_name': 'active'}}

    def _parse_get_weather(self, text: str) -> Dict[str, Any]:
        patterns = [
            r'weather in (.+)', 
            r'weather for (.+)', 
            r'weather at (.+)',
            r'forecast for (.+)', 
            r'weather of (.+)',
            r'weather (.+)'
        ]
        for pattern in patterns:
            match = re.search(pattern, text.lower())
            if match:
                location = re.sub(r'\b(today|tomorrow|now|at|in|of|for)\b', '', match.group(1)).strip()
                return {'function_name': 'get_weather', 'parameters': {'city': location or 'current'}}
        return {'function_name': 'get_weather', 'parameters': {'city': 'current'}}

    def _parse_search_web(self, text: str) -> Dict[str, Any]:
        patterns = [r'search for (.+)', r'look up (.+)', r'find (.+)', r'google (.+)', r'search (.+)']
        for pattern in patterns:
            match = re.search(pattern, text.lower())
            if match:
                return {'function_name': 'search_web', 'parameters': {'query': match.group(1).strip()}}
        return {'function_name': 'search_web', 'parameters': {'query': text}}

    def _parse_type_text(self, text: str) -> Dict[str, Any]:
        patterns = [r'type (.+)', r'write (.+)', r'input (.+)', r'enter (.+)']
        for pattern in patterns:
            match = re.search(pattern, text.lower())
            if match:
                return {'function_name': 'type_text', 'parameters': {'text': match.group(1).strip()}}
        return {'function_name': 'type_text', 'parameters': {'text': text}}

    def _parse_press_key(self, text: str) -> Dict[str, Any]:
        keys = {
            'enter': 'enter', 'return': 'enter', 'space': 'space', 'spacebar': 'space',
            'escape': 'escape', 'esc': 'escape', 'tab': 'tab', 'backspace': 'backspace',
            'delete': 'delete', 'shift': 'shift', 'control': 'ctrl', 'ctrl': 'ctrl',
            'alt': 'alt', 'windows': 'win', 'win': 'win'
        }
        for key_name, key_code in keys.items():
            if key_name in text.lower():
                return {'function_name': 'press_key', 'parameters': {'key': key_code}}
        return {'function_name': 'press_key', 'parameters': {'key': 'enter'}}

    def _parse_take_screenshot(self, text: str) -> Dict[str, Any]:
        return {'function_name': 'take_screenshot', 'parameters': {}}

    def _parse_read_screen(self, text: str) -> Dict[str, Any]:
        return {'function_name': 'read_screen', 'parameters': {}}

    def _parse_adjust_volume(self, text: str) -> Dict[str, Any]:
        t = text.lower()
        if (m := re.search(r'volume to (\d+)', t)):
            return {'function_name': 'adjust_volume', 'parameters': {'volume_level': int(m.group(1))}}
        for inc in ['up', 'higher', 'increase', 'boost']:
            if inc in t:
                return {'function_name': 'adjust_volume', 'parameters': {'action': 'increase'}}
        for dec in ['down', 'lower', 'decrease', 'reduce']:
            if dec in t:
                return {'function_name': 'adjust_volume', 'parameters': {'action': 'decrease'}}
        if 'mute' in t: return {'function_name': 'adjust_volume', 'parameters': {'action': 'mute'}}
        if 'unmute' in t: return {'function_name': 'adjust_volume', 'parameters': {'action': 'unmute'}}
        return {'function_name': 'adjust_volume', 'parameters': {'action': 'toggle'}}

    def _parse_get_current_time(self, text: str) -> Dict[str, Any]:
        return {'function_name': 'get_current_time', 'parameters': {}}

    def _parse_get_current_date(self, text: str) -> Dict[str, Any]:
        return {'function_name': 'get_current_date', 'parameters': {}}

    def _parse_send_email(self, text: str) -> Dict[str, Any]:
        t = text.lower()
        email_match = re.search(r'[\w\.-]+@[\w\.-]+\.\w+', t)
        subject_match = re.search(r'subject (.+)', t)
        parameters = {}
        if email_match: parameters['to'] = email_match.group(0)
        if subject_match: parameters['subject'] = subject_match.group(1).strip()
        return {'function_name': 'send_email', 'parameters': parameters}

    def _parse_open_file(self, text: str) -> Dict[str, Any]:
        for pattern in [r'open (.+)', r'open file (.+)', r'load (.+)', r'load file (.+)']:
            match = re.search(pattern, text.lower())
            if match:
                return {'function_name': 'open_file', 'parameters': {'file_path': match.group(1).strip()}}
        return {'function_name': 'open_file', 'parameters': {'file_path': 'unknown'}}

    def _parse_scroll_mouse(self, text: str) -> Dict[str, Any]:
        t = text.lower()
        direction = 'down' if 'down' in t else 'up'
        amount = int(re.search(r'(\d+)', t).group(1)) if re.search(r'(\d+)', t) else 1000
        return {'function_name': 'scroll_mouse', 'parameters': {'direction': direction, 'amount': amount}}

    def _parse_click_mouse(self, text: str) -> Dict[str, Any]:
        t = text.lower()
        if 'right' in t: button = 'right'
        elif 'double' in t: button = 'double'
        else: button = 'left'
        return {'function_name': 'click_mouse', 'parameters': {'button': button}}

    def _parse_move_cursor(self, text: str) -> Dict[str, Any]:
        match = re.search(r'(\d+)[^\d]+(\d+)', text)
        if match:
            return {'function_name': 'move_cursor', 'parameters': {'x': int(match.group(1)), 'y': int(match.group(2))}}
        return {'function_name': 'move_cursor', 'parameters': {}}

    def _parse_get_cursor_position(self, text: str) -> Dict[str, Any]:
        return {'function_name': 'get_cursor_position', 'parameters': {}}

    def _parse_get_screen_size(self, text: str) -> Dict[str, Any]:
        return {'function_name': 'get_screen_size', 'parameters': {}}

    def _parse_run_command(self, text: str) -> Dict[str, Any]:
        match = re.search(r'run (.+)', text.lower())
        command = match.group(1).strip() if match else text
        return {'function_name': 'run_command', 'parameters': {'command': command}}

    def _parse_start_interview_session(self, text: str) -> Dict[str, Any]:
        return {'function_name': 'start_interview_session', 'parameters': {}}

    def _parse_get_next_question(self, text: str) -> Dict[str, Any]:
        return {'function_name': 'get_next_question', 'parameters': {}}

    def _parse_set_resume_path(self, text: str) -> Dict[str, Any]:
        match = re.search(r'set.*resume.*to (.+)', text.lower())
        path = match.group(1).strip() if match else 'unknown'
        return {'function_name': 'set_resume_path', 'parameters': {'resume_path': path}}

    def _parse_tell_about_yourself(self, text: str) -> Dict[str, Any]:
        return {'function_name': 'tell_about_yourself', 'parameters': {}}

    def _parse_evaluate_interview(self, text: str) -> Dict[str, Any]:
        return {'function_name': 'evaluate_interview', 'parameters': {}}

    def _parse_check_code_solution(self, text: str) -> Dict[str, Any]:
        return {'function_name': 'check_code_solution', 'parameters': {}}
