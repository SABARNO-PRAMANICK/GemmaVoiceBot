# Use official Python 3.12 slim image as base
FROM python:3.12-slim

# Install system dependencies for PyAudio and other libs
RUN apt-get update && apt-get install -y \
    build-essential \
    gcc \
    portaudio19-dev \
    pulseaudio-utils \
    libasound2-dev \
    git \
    ffmpeg \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install mpv for cross-platform audio playback (optional)
RUN apt-get update && apt-get install -y mpv && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy requirements
COPY requirements.txt /app/requirements.txt

# Install python dependencies
RUN pip install --upgrade pip
RUN pip install -r requirements.txt

# Copy app code
COPY . /app

# Expose ports (if needed, none for this CLI app)

# Default command to run the app
CMD ["python", "ai_voice_agent_fixed.py"]
