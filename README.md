# Luma - On-Device AI-Powered System Control with Ollama and TTS 🤖

This project provides an On-Device AI-driven interface for interacting with your system. It leverages the llama3.2 LLM to understand user commands and the `kokoro` TTS library to provide voice feedback. It allows you to control various system functions like screen brightness, volume, media playback, and power management, all through natural language.

## 🚀 Key Features

- **Natural Language Control:** Interact with your system using natural language commands processed by the Ollama language model.
- **System Control Tools:** Control screen brightness, volume, media playback (play, pause, next, previous), and power management (lock, suspend, shutdown).
- **Text-to-Speech Feedback:**  Receive voice feedback for your commands using the `kokoro` TTS library.
- **Docker Support:**  Seamlessly runs both natively and within a Docker container (use Docker for ease of use).
- **Asynchronous Processing:** Utilizes threads and queues for asynchronous text-to-speech processing, ensuring smooth performance.
- **Configurable:** Easily customize the application's behavior through the `config.conf` file.
- **Error Logging:** Comprehensive logging using a custom `LOGS` module.
- **Interrupt Handling:** Allows users to interrupt long-running processes.

## 🛠️ Tech Stack

*   **Language Model:** Ollama (llama3.2)
*   **Text-to-Speech:** `kokoro`
*   **Programming Language:** Python
*   **HTTP Requests:** `requests`
*   **Numerical Operations:** `numpy`
*   **Threading & Queues:** `threading`, `queue`
*   **Configuration Parsing:** `configparser`
*   **Subprocess Management:** `subprocess`
*   **Signal Handling:** `signal`
*   **Docker Detection:** `os`
*   **Temporary Files:** `tempfile`
*   **Logging:** Custom `LOGS` module
*   **Testing:** Custom `tests` module
*   **Deep Learning Framework:** `torch` (PyTorch)

## 📦 Getting Started

### Prerequisites

*   Ollama installed and running
*   Docker with docker compose installed
*   Makefile utilities installed

### Installation

1.  Clone the repository:

    ```bash
    git clone https://github.com/MatriX1232/Luma
    cd Luma
    ```

2.  Install Ollama and then:

    ```bash
    NEED TO FINISH INSTALL INSTRUCTIONS ...
    ```

3.  Configure `config.conf`:

    *   Modify the `config.conf` file to set the desired `model_name`, and `use_tools` parameters.

### Running Locally

1.  Start the Ollama server (if not already running).

2.  Run the `Makefile` script:

    ```bash
    sudo make start
    ```

## 💻 Usage

Once the application is running, you can interact with it by typing commands into the console. The AI will process your commands and perform the requested actions. For example:

*   "Set the screen brightness to 50%"
*   "Increase the volume"
*   "Play music"
*   "Lock the screen"
*   "Explain C++ in 10 words"
*   "My screen is a little bit too bright, could u turn it down?"

The application will provide voice feedback to confirm the actions taken.

## 📝 License

This project is licensed under the [MIT License](LICENSE).
