# Luma

Simple local assistant utilities and tests.

Requirements
- Python 3.12
- Optional GPU: NVIDIA drivers + CUDA (nvidia-smi)
- Ollama installed and available on PATH (for model serving)
- Recommended Python packages (example):
    - colored
    - transformers
    - torch
    - soundfile
    - kokoro (for TTS pipeline)

Quick install
1. Create a Python 3.12 venv:
     python3.12 -m venv .venv && source .venv/bin/activate
2. Install packages:
     pip install colored transformers torch soundfile kokoro

Configuration
- Edit `config.conf`:
    - PERFORM_TESTS = true|false
    - MAIN_MODEL (eg. `llama3.2`)
    - TTS_MODEL (eg. `kokoro`)
    - USE_GPU = true|false

Notes about CUDA / GPU
- To use GPU features enable `USE_GPU=true` and ensure NVIDIA drivers/CUDA are installed.
- `nvidia-smi` must be present and Ollama should be able to access CUDA-enabled devices.
- Ollama is used for serving Llama models (see tests that call `ollama serve` and `ollama list`).

Running
- Run the app:
    python main.py
- If `PERFORM_TESTS=true` the script runs basic checks:
    - Python version
    - ollama presence and model listing
    - nvidia-smi / CUDA availability
    - attempts to start `ollama serve`

TTS
- Example pipeline in `TTS_MODEL.py` uses Kokoro to generate .wav files.

Project files
- main.py — launcher and test orchestration
- tests.py — simple subprocess-based checks
- LOGS.py — colored logging helpers
- config.conf — runtime configuration
- TTS_MODEL.py — example TTS usage

License
- Personal / internal project (add a license file as needed)