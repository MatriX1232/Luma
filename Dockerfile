FROM nvidia/cuda:13.0.1-runtime-ubuntu22.04

ENV DEBIAN_FRONTEND=noninteractive
ENV LANG=C.UTF-8
WORKDIR /app

# Add deadsnakes PPA for Python 3.12 on Ubuntu 22.04
RUN apt-get update && apt-get install -y --no-install-recommends \
    software-properties-common curl \
  && add-apt-repository -y ppa:deadsnakes/ppa \
  && apt-get update && apt-get install -y --no-install-recommends \
    python3.12 python3.12-venv python3.12-dev \
    ca-certificates ffmpeg libsndfile1 libasound2 pulseaudio-utils git \
  && rm -rf /var/lib/apt/lists/*

# Set Python 3.12 as default
RUN ln -sf /usr/bin/python3.12 /usr/bin/python3 \
  && ln -sf /usr/bin/python3.12 /usr/bin/python

# Install pip via get-pip.py (distutils no longer exists in 3.12)
RUN curl -sS https://bootstrap.pypa.io/get-pip.py | python \
  && python -m pip install --upgrade pip setuptools wheel

COPY requirements.txt /app/requirements.txt
COPY config.conf /app/config.conf
RUN pip install --no-cache-dir -r /app/requirements.txt

# Install CUDA-13 compatible torch wheel (adjust if you prefer a specific build)
RUN pip install --no-cache-dir torch --index-url https://download.pytorch.org/whl/cu130

COPY . /app
ENV PYTHONUNBUFFERED=1

# ENTRYPOINT ["bash"]
ENTRYPOINT ["python", "main.py"]