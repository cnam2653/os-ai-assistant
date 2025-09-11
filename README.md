OS AI Assistant
The OS AI Assistant is a personal desktop assistant, inspired by the AI from the movie Iron Man, which allows you to control your computer using natural language voice commands. It features a hybrid smart routing system that uses a local intent classification model for core commands and falls back to a large language model (LLM) for more complex tasks. The assistant's persona is that of a classy and sarcastic butler named Jarvis.

Features
The assistant has a wide range of capabilities to help you manage your computer and daily tasks:

System Control: Open applications, control the mouse and keyboard, take screenshots, and run command line commands.

Information Retrieval: Get the current weather for a city, search the web, and check the current time and date.

Communication: Send emails through a configured Gmail account.

Mock Interviews: Conduct mock interviews, including both behavioral and technical questions, and provide feedback and a final evaluation.

Installation
To install and run the project, you need to set up the environment and install the required dependencies.

Clone the Repository:

Bash

git clone https://github.com/your-username/os-ai-assistant.git
cd os-ai-assistant
Create a Virtual Environment:
It is recommended to use a virtual environment to manage dependencies.

Bash

python -m venv venv
Activate the Virtual Environment:

On Windows: venv\Scripts\activate

On macOS/Linux: source venv/bin/activate

Install Dependencies:
The project uses a variety of libraries for its functionality, including livekit for agent sessions, pyautogui for GUI automation, and psutil for system process management.

Bash

pip install -r requirement.txt
(Note: Some features like audio control (pycaw, comtypes) are Windows-specific).

Set Environment Variables:
Create a .env file in the project root to store your API keys and credentials. A .gitignore file is included to prevent this file from being committed to the repository.

Ini, TOML

# .env
PORCUPINE_ACCESS_KEY="your-access-key"
GMAIL_USER="your-email@gmail.com"
GMAIL_APP_PASSWORD="your-app-password"
OPENAI_API_KEY="your-openai-api-key"
REDIS_HOST="localhost"
REDIS_PORT=6379
REDIS_DB=0
Usage
Training the Intent Classifier
The assistant uses a local intent classifier to quickly handle common commands. You can train the model with your own data:

Run the Training Script:
The run_training.py script automates the data augmentation and model training process.

Bash

python run_training.py
This script will create augmented data in data/intents_augmented.csv and save the trained model to the intent_model/ directory.

Running the Assistant
Once the environment is set up, you can run the main script. The assistant listens for the wake word "Jarvis".

Bash

python main.py
Project Structure
main.py: The main entry point of the application, managing the livekit agent session, speech recognition, and local function parsing.

prompts.py: Defines the persona and instructions for the Jarvis assistant.

requirements.txt: Lists all necessary Python dependencies.

run_training.py: A utility script to automate the data augmentation and model training process.

local_intent_parser.py: The core of the local command system, which classifies user input and extracts parameters for function calls.

jarvis_memory.py: Handles conversation history, command logging, and user preferences using Redis.

data/: Contains the original and augmented datasets (intents.csv and intents_augmented.csv) for training the intent classifier.

tools/: A directory containing modular tool scripts for specific functionalities:

web_utils.py: Tools for web-related tasks.

os_commands.py: Tools for interacting with the operating system.

mouse_key.py: Tools for controlling the mouse and keyboard.

interview.py: Tools for conducting mock interviews and providing feedback.

screen.py: Tools for taking and reading screenshots.

audio_control.py: Tools for adjusting system volume.

Acknowledgements
LiveKit: For providing the agent and real-time communication framework.

Picovoice Porcupine: For the wake word detection engine.

PyAutoGUI & PSUtil: For system automation and process management.
