# Use official Python 3.12 slim image as base
FROM python:3.12-slim

# Install system dependencies for PyAudio, audio, and other libs (combined for efficiency)
RUN apt-get update && apt-get install -y \
    build-essential \
    gcc \
    portaudio19-dev \
    pulseaudio-utils \
    libasound2-dev \
    git \
    ffmpeg \
    curl \
    pulseaudio \
    libpulse-dev \
    libasound2-plugins \
    && apt-get install -y mpv \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy requirements and install (upgraded pip with wheel for faster installs)
COPY requirements.txt /app/requirements.txt
RUN pip install --upgrade pip setuptools wheel
RUN pip install -r requirements.txt

# Copy app code
COPY . /app

# Default command to run the app
CMD ["python", "ai_voice_agent_fixed.py"]
