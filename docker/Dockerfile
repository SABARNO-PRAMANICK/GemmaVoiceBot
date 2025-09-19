# Multi-stage Dockerfile to pull Ollama model during build

# Stage 1: Pull Ollama model using official Ollama image
FROM ollama/ollama AS ollama-builder

# Start Ollama server in background, wait, and pull the model
RUN ollama serve & sleep 5 && ollama pull gemma3:1b

# Stage 2: Main Python app image
FROM python:3.12-slim

# Install system dependencies for PyAudio and other libs (including build tools for compiling)
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

# Install MPV for audio playback if needed (optional)
RUN apt-get update && apt-get install -y mpv && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy requirements file (create your own or use below)
COPY requirements.txt /app/requirements.txt

# Install Python dependencies
RUN pip install --upgrade pip
RUN pip install -r requirements.txt

# Copy your app code
COPY . /app

# Set environment variables for Ollama
ENV OLLAMA_REPO=/ollama_repo

# Copy the pulled model from builder stage
COPY --from=ollama-builder /root/.ollama /root/.ollama

# Install Ollama Python client (for app usage)
RUN pip install ollama

# Expose any ports if required (not necessary for CLI apps)
# EXPOSE 8000

# Default command to run the app
CMD ["python", "ai_voice_agent_fixed.py"]
