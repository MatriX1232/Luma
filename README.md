# Luma – Terminal AI Assistant with TTS

Luma is a terminal-based AI assistant that uses Ollama for language generation and Kokoro for text-to-speech synthesis. It runs entirely in your terminal with optional GPU acceleration via Docker.

## Features

- **Interactive terminal chat** – converse with an AI model directly in your terminal
- **Real-time text-to-speech** – responses are spoken aloud as they stream in
- **GPU acceleration** – NVIDIA CUDA support for faster inference
- **Dockerized** – consistent environment with full GPU and audio passthrough

## Prerequisites

### Host Requirements

| Requirement | Notes |
|-------------|-------|
| **NVIDIA GPU** | With up-to-date drivers (`nvidia-smi` should work) |
| **Docker** | Docker Engine 20.10+ with Compose v2 |
| **NVIDIA Container Toolkit** | For GPU passthrough to containers |
| **PulseAudio** | For audio playback (default on most Linux desktops) |
| **Ollama** | Running on host or accessible via network |

### Installing NVIDIA Container Toolkit

#### Fedora

```bash
# Add NVIDIA repo
curl -s -L https://nvidia.github.io/libnvidia-container/stable/rpm/nvidia-container-toolkit.repo | \
  sudo tee /etc/yum.repos.d/nvidia-container-toolkit.repo

# Install toolkit
sudo dnf install -y nvidia-container-toolkit

# Configure Docker runtime
sudo nvidia-ctk runtime configure --runtime=docker
sudo systemctl restart docker

# Verify
docker run --rm --gpus all nvidia/cuda:13.0.1-runtime-ubuntu22.04 nvidia-smi
```

#### Ubuntu / Debian

```bash
distribution=$(. /etc/os-release; echo $ID$VERSION_ID)
curl -s -L https://nvidia.github.io/nvidia-docker/gpgkey | sudo apt-key add -
curl -s -L https://nvidia.github.io/nvidia-docker/$distribution/nvidia-docker.list | \
  sudo tee /etc/apt/sources.list.d/nvidia-docker.list

sudo apt-get update
sudo apt-get install -y nvidia-container-toolkit
sudo nvidia-ctk runtime configure --runtime=docker
sudo systemctl restart docker

# Verify
docker run --rm --gpus all nvidia/cuda:13.0.1-runtime-ubuntu22.04 nvidia-smi
```

### Installing Ollama (on host)

```bash
curl -fsSL https://ollama.com/install.sh | sh

# Start Ollama server
ollama serve &

# Pull a model (e.g., llama3.2)
ollama pull llama3.2
```

## Installation

### 1. Clone the repository

```bash
git clone https://github.com/YOUR_USERNAME/Luma.git
cd Luma
```

### 2. Configure

Edit `config.conf` to set your preferences:

```ini
[DEFAULT]
MAIN_MODEL = llama3.2
TTS_MODEL = default
USE_GPU = True
PERFORM_TESTS = False
```

| Option | Description |
|--------|-------------|
| `MAIN_MODEL` | Ollama model name (must be pulled first) |
| `TTS_MODEL` | TTS voice/model (default works) |
| `USE_GPU` | `True` for CUDA acceleration, `False` for CPU |
| `PERFORM_TESTS` | Run startup tests (Ollama, CUDA checks) |

### 3. Build the Docker image

```bash
docker compose build
```

## Usage

### Interactive Terminal Session

```bash
# Start interactive container (recommended)
docker compose run --rm luma
```

### Direct Docker Run (without Compose)

```bash
docker run --rm -it --gpus all \
  -e PYTHONUNBUFFERED=1 \
  -e PULSE_SERVER=unix:/run/user/$(id -u)/pulse/native \
  -v "$(pwd)":/app \
  -v /run/user/$(id -u)/pulse/native:/run/user/$(id -u)/pulse/native \
  -v /dev/snd:/dev/snd \
  --group-add audio \
  luma:gpu python main.py
```

### Example Session

```
$ docker compose run --rm luma
root@container:/app# python main.py
You: Hello, who are you?
AI: I'm Luma, your terminal AI assistant! I can help answer questions, 
    have conversations, and more. What would you like to talk about?
You: exit
```

## Audio Troubleshooting

### PulseAudio socket path

The default config assumes UID 1000. Find your UID and update `docker-compose.yaml` if different:

```bash
id -u
# If not 1000, replace all instances of 1000 in docker-compose.yaml
```

### No audio output

1. Check PulseAudio is running: `pactl info`
2. Verify socket exists: `ls -la /run/user/$(id -u)/pulse/native`
3. Try ALSA fallback (already configured via `/dev/snd` passthrough)

### Permission denied on /dev/snd

Add your user to the `audio` group or run with `--privileged` (not recommended for production).

## GPU Troubleshooting

### "could not select device driver with capabilities: [[gpu]]"

NVIDIA Container Toolkit is not installed or configured. Follow the installation steps above.

### Verify GPU access inside container

```bash
docker compose run --rm luma nvidia-smi
```

## Development

### Run without Docker (native)

```bash
# Create virtual environment
python -m venv .venv
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt
pip install torch --index-url https://download.pytorch.org/whl/cu130

# Run
python main.py
```

### Run tests

```bash
# Inside container or native
python tests.py
```

## License

MIT License – see LICENSE file for details.
