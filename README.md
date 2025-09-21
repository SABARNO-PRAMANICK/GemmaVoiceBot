# AI Voice Agent (Whisper STT + Groq PlayAI TTS)

A Python 3.12 voice assistant that listens through your microphone, transcribes speech with Whisper, feeds it to a Groq-powered LLM, and replies with PlayAI TTS in real time.  
Run it either (a) directly with the ultra-fast **uv** runtime or (b) as a pre-built Docker image from Docker Hub.

---

## ✨ Features

* Real-time microphone capture (PyAudio / ALSA)  
* Whisper-large-v3 transcription  
* Groq LLM for conversational logic  
* Groq PlayAI TTS streaming playback  
* Single-file Docker image (python:3.12-slim)

---

## 🏃‍♂️ Quick Start — Docker

1 – Pull image
```
docker pull sabarnopingbix/ai-voice-agent:latest
```

2 – Run (replace the two keys with your own)
```
docker run -it --privileged \
-e ASSEMBLYAI_API_KEY="YOUR_ASSEMBLYAI_KEY" \
-e GROQ_API_KEY="YOUR_GROQ_KEY" \
sabarnopingbix/ai-voice-agent:latest
```

> **Windows / WSL 2 note**  
> • `--privileged` lets the container access audio.  
> • If `--device /dev/snd` fails, omit it and use the PulseAudio socket method below.

---

## 🖥️ Run Locally with **uv**

1 – Clone and enter the repo
```
git clone https://github.com/SABARNO-PRAMANICK/GemmaVoiceBot.git
cd GemmaVoiceBot
```

2 – Install deps (uv pip is ~2–3× faster)
```
uv pip install -r requirements.txt
```

3 – Run the agent
```
ASSEMBLYAI_API_KEY="YOUR_ASSEMBLYAI_KEY" \
GROQ_API_KEY="YOUR_GROQ_KEY" \
uv run ai_voice_agent_fixed.py
```

---

## 🔑 Required Environment Variables

| Variable             | Purpose                                   |
|----------------------|-------------------------------------------|
| `ASSEMBLYAI_API_KEY` | Whisper STT / AssemblyAI access           |
| `GROQ_API_KEY`       | Groq LLM + Groq PlayAI TTS                |

---

## 🔈 Audio on Windows (WSL 2)

Docker on Windows cannot map `/dev/snd`.  
If you need microphone playback inside the container:

Start PulseAudio server on Windows (example)
```
C:\PulseAudio\bin\pulseaudio.exe
```

Run container with PulseAudio socket mount
```
docker run -it --privileged \
-v /run/user/1000/pulse:/run/user/1000/pulse \
-e PULSE_SERVER=unix:/run/user/1000/pulse/native \
-e ASSEMBLYAI_API_KEY="YOUR_ASSEMBLYAI_KEY" \
-e GROQ_API_KEY="YOUR_GROQ_KEY" \
sabarnopingbix/ai-voice-agent:latest
```

---

## 🛠️ Build the Image Yourself

```
docker build -t ai-voice-agent .
docker run -it --privileged \
-e ASSEMBLYAI_API_KEY="YOUR_ASSEMBLYAI_KEY" \
-e GROQ_API_KEY="YOUR_GROQ_KEY" \
ai-voice-agent
```

---

## 📄 License

MIT © 2025 sabarnopingbix