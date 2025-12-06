FROM nvidia/cuda:13.0.1-runtime-ubuntu22.04

ENV DEBIAN_FRONTEND=noninteractive
ENV LANG=C.UTF-8
WORKDIR /app

# Install system Python 3.10 (Ubuntu default) plus GTK and audio deps
RUN apt-get update && apt-get install -y --no-install-recommends \
        python3 python3-venv python3-dev python3-pip \
        ca-certificates curl ffmpeg libsndfile1 libasound2 pulseaudio-utils git \
        libgtk-3-0 libgtk-3-dev \
        pkg-config libgirepository1.0-dev libcairo2-dev gobject-introspection \
        gir1.2-gtk-3.0 gir1.2-glib-2.0 \
        util-linux \
        python3-gi python3-gi-cairo \
    && rm -rf /var/lib/apt/lists/*

# Ensure pip is up to date
RUN python3 -m pip install --upgrade pip setuptools wheel

# (PyGObject is provided by python3-gi; no extra pip install needed)

# Copy requirements first (for better layer caching)
COPY requirements.txt /app/requirements.txt

# Install Python packages with BuildKit cache mount
RUN --mount=type=cache,target=/root/.cache/pip \
    pip install -r /app/requirements.txt

# Install CUDA-13 compatible torch with cache
RUN --mount=type=cache,target=/root/.cache/pip \
    pip install torch --index-url https://download.pytorch.org/whl/cu130

# Copy the rest of the app (changes here won't invalidate pip cache)
COPY config.conf /app/config.conf
COPY . /app

ENV PYTHONUNBUFFERED=1
ENV DISPLAY=:0

# ENTRYPOINT ["bash"]
ENTRYPOINT ["python3", "main.py"]