# OS AI Assistant

The OS AI Assistant is a personal desktop assistant, inspired by the AI from the movie *Iron Man*, which allows you to control your computer using natural language voice commands. It features a hybrid smart routing system that uses a local intent classification model for core commands and falls back to a large language model (LLM) for more complex tasks. The assistant's persona is that of a classy and sarcastic butler named Jarvis.

## Features

The assistant has a wide range of capabilities to help you manage your computer and daily tasks:

* **System Control**: Open applications, control the mouse and keyboard, take screenshots, and run command line commands.
* **Information Retrieval**: Get the current weather for a city, search the web, and check the current time and date.
* **Communication**: Send emails through a configured Gmail account.
* **Mock Interviews**: Conduct mock interviews, including both behavioral and technical questions, and provide feedback and a final evaluation.

## Installation

To install and run the project, you need to set up the environment and install the required dependencies.

1.  **Clone the Repository**:
    ```bash
    git clone [https://github.com/your-username/os-ai-assistant.git](https://github.com/your-username/os-ai-assistant.git)
    cd os-ai-assistant
    ```

2.  **Create a Virtual Environment**:
    It is recommended to use a virtual environment to manage dependencies.
    ```bash
    python -m venv venv
    ```

3.  **Activate the Virtual Environment**:
    * On Windows: `venv\Scripts\activate`
    * On macOS/Linux: `source venv/bin/activate`

4.  **Install Dependencies**:
    The project uses a variety of libraries for its functionality, including `livekit` for agent sessions, `pyautogui` for GUI automation, and `psutil` for system process management.
    ```bash
    pip install -r requirement.txt
    ```
    (Note: Some features like audio control (`pycaw`, `comtypes`) are Windows-specific).

5.  **Set Environment Variables**:
    Create a `.env` file in the project root to store your API keys and credentials. A `.gitignore` file is included to prevent this file from being committed to the repository.

    ```ini
    # .env
    PORCUPINE_ACCESS_KEY="your-access-key"
    GMAIL_USER="your-email@gmail.com"
    GMAIL_APP_PASSWORD="your-app-password"
    OPENAI_API_KEY="your-openai-api-key"
    REDIS_HOST="localhost"
    REDIS_PORT=6379
    REDIS_DB=0
    ```

## Usage

### Training the Intent Classifier

The assistant uses a local intent classifier to quickly handle common commands. You can train the model with your own data:

1.  **Run the Training Script**:
    The `run_training.py` script automates the data augmentation and model training process.
    ```bash
    python run_training.py
    ```
    This script will create augmented data in `data/intents_augmented.csv` and save the trained model to the `intent_model/` directory.

### Running the Assistant

Once the environment is set up, you can run the main script. The assistant listens for the wake word "Jarvis".

```bash
python main.py
