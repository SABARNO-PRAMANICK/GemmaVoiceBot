import pyaudio
import websocket
import json
import threading
import time
from urllib.parse import urlencode
from datetime import datetime
import os
from dotenv import load_dotenv
from groq import Groq
import io
import tempfile

load_dotenv()

# --- Configuration ---
YOUR_API_KEY = os.getenv("ASSEMBLYAI_API_KEY")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")

if not YOUR_API_KEY:
    raise ValueError("ASSEMBLYAI_API_KEY not found in .env file")
if not GROQ_API_KEY:
    raise ValueError("GROQ_API_KEY not found in .env file")

CONNECTION_PARAMS = {
    "sample_rate": 16000,
    "format_turns": True,  # Request formatted final transcripts
}
API_ENDPOINT_BASE_URL = "wss://streaming.assemblyai.com/v3/ws"
API_ENDPOINT = f"{API_ENDPOINT_BASE_URL}?{urlencode(CONNECTION_PARAMS)}"

# Audio Configuration
FRAMES_PER_BUFFER = 800  # 50ms of audio (0.05s * 16000Hz)
SAMPLE_RATE = CONNECTION_PARAMS["sample_rate"]
CHANNELS = 1
FORMAT = pyaudio.paInt16

# Global variables for audio stream and websocket
audio = None
stream_audio = None
ws_app = None
audio_thread = None
stop_event = threading.Event()  # To signal the audio thread to stop

# Groq client for TTS and chat completions
groq_client = Groq(api_key=GROQ_API_KEY)

# Conversation history
full_transcript = [
    {"role": "system", 
     "content": (
        "You are PingBix AI Assistant, a helpful, intelligent AI assistant created by Pingbix.com .\n"
        "- Respond accurately and informatively.\n"
        "- Use 25 words maximum, conversational but specific.\n"
        "- Avoid repetition and overused emojis. Never reply with just emojis.\n"
        "- Ask relevant follow-up questions sometimes for engagement.\n"
        "- Provide details/examples if helpful.\n"
        "- Be natural, engaging, and respond uniquely every time."
    )}
]

# Processing state
is_processing = False
processing_lock = threading.Lock()

def play_audio_windows(audio_data):
    """Play audio on Windows using winsound"""
    try:
        import winsound

        # Save audio data to temporary file
        with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as temp_file:
            temp_file.write(audio_data)
            temp_file_path = temp_file.name

        # Play the audio file
        winsound.PlaySound(temp_file_path, winsound.SND_FILENAME)

        # Clean up
        os.unlink(temp_file_path)

    except ImportError:
        print(" [Windows audio not available]", end="")
    except Exception as e:
        print(f" [Audio playback error: {e}]", end="")

def play_audio_cross_platform(audio_data):
    """Cross-platform audio playback"""
    try:
        # Try pygame first (works on all platforms)
        import pygame
        pygame.mixer.init()

        # Create a BytesIO object from audio data
        audio_io = io.BytesIO(audio_data)
        pygame.mixer.music.load(audio_io)
        pygame.mixer.music.play()

        # Wait for playback to finish
        while pygame.mixer.music.get_busy():
            time.sleep(0.1)

    except ImportError:
        # Fallback to platform-specific methods
        import platform
        if platform.system() == "Windows":
            play_audio_windows(audio_data)
        else:
            print(" [Audio playback not available - install pygame]", end="")
    except Exception as e:
        print(f" [Audio error: {e}]", end="")

def generate_speech_groq(text):
    try:
        response = groq_client.audio.speech.create(
            model="playai-tts",
            voice="Arista-PlayAI",
            input=text,
            response_format="wav"
        )
        
        # Try different methods to extract audio data
        if hasattr(response, 'content'):
            audio_data = response.content
        elif hasattr(response, 'read'):
            audio_data = response.read()
        elif hasattr(response, '__iter__'):
            audio_data = b''.join(response)
        else:
            audio_data = bytes(response)
        
        return audio_data

    except Exception as e:
        print(f" [Groq TTS Error: {e}]", end="")
        return None

def generate_ai_response(transcript_text):
    """Generate AI response using Groq llama-3.1-8b-instant and convert to speech with Groq"""
    global is_processing, full_transcript

    with processing_lock:
        if is_processing:
            return
        is_processing = True

    try:
        # Add user message to conversation history
        full_transcript.append({"role": "user", "content": transcript_text})
        print(f"\n👤 User: {transcript_text}")

        # Generate response with Groq
        print("🤖 Groq: ", end="", flush=True)

        # Send full history as messages
        completion = groq_client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=full_transcript,
            temperature=1,
            max_tokens=1024,  # Note: max_tokens instead of max_completion_tokens for consistency
            top_p=1,
            stream=True,
            stop=None
        )

        text_buffer = ""
        full_text = ""

        for chunk in completion:
            chunk_text = chunk.choices[0].delta.content or ""
            text_buffer += chunk_text
            full_text += chunk_text

            # Convert complete sentences to speech
            if text_buffer.endswith('.') or text_buffer.endswith('!') or text_buffer.endswith('?'):
                if text_buffer.strip():
                    print(text_buffer, end="", flush=True)

                    # Generate speech with Groq TTS
                    audio_data = generate_speech_groq(text_buffer.strip())
                    if audio_data:
                        play_audio_cross_platform(audio_data)

                    text_buffer = ""

        # Handle any remaining text
        if text_buffer.strip():
            print(text_buffer)
            audio_data = generate_speech_groq(text_buffer.strip())
            if audio_data:
                play_audio_cross_platform(audio_data)
            full_text += text_buffer

        # Add assistant response to conversation history
        full_transcript.append({"role": "assistant", "content": full_text})

        # Keep conversation history manageable (last 10 exchanges)
        if len(full_transcript) > 21:  # system + 20 messages
            full_transcript = [full_transcript[0]] + full_transcript[-20:]

        print("\n")

    except Exception as e:
        print(f"\n❌ Error generating AI response: {e}")
        error_message = "Sorry, I'm having trouble processing that right now."
        print(f"🤖 Groq: {error_message}")
    finally:
        is_processing = False

# --- WebSocket Event Handlers ---

def on_open(ws):
    """Called when the WebSocket connection is established."""
    print("✅ WebSocket connection opened")
    print(f"🔗 Connected to: {API_ENDPOINT}")

    # Start sending audio data in a separate thread
    def stream_audio_data():
        global stream_audio
        print("📡 Starting audio streaming...")
        while not stop_event.is_set():
            try:
                audio_data = stream_audio.read(FRAMES_PER_BUFFER, exception_on_overflow=False)
                # Send audio data as binary message
                ws.send(audio_data, websocket.ABNF.OPCODE_BINARY)
            except Exception as e:
                print(f"❌ Error streaming audio: {e}")
                # If stream read fails, likely means it's closed, stop the loop
                break
        print("📡 Audio streaming stopped")

    global audio_thread
    audio_thread = threading.Thread(target=stream_audio_data)
    audio_thread.daemon = True
    audio_thread.start()

def on_message(ws, message):
    try:
        data = json.loads(message)
        msg_type = data.get('type')

        if msg_type == "Begin":
            session_id = data.get('id')
            expires_at = data.get('expires_at')
            print(f"\n🎯 Session started: {session_id}")
            print(f"⏰ Expires: {datetime.fromtimestamp(expires_at)}")
            print("🎤 Start speaking...")
        elif msg_type == "Turn":
            transcript = data.get('transcript', '')
            formatted = data.get('turn_is_formatted', False)

            # Clear previous line for formatted messages
            if formatted:
                print('\r' + ' ' * 80 + '\r', end='')
                if transcript.strip() and not is_processing:
                    # Process the final transcript with AI in a separate thread
                    threading.Thread(
                        target=generate_ai_response,
                        args=(transcript,),
                        daemon=True
                    ).start()
            else:
                print(f"\r🎤 {transcript}", end='', flush=True)
        elif msg_type == "Termination":
            audio_duration = data.get('audio_duration_seconds', 0)
            session_duration = data.get('session_duration_seconds', 0)
            print(f"\n🔚 Session ended: Audio {audio_duration:.1f}s, Session {session_duration:.1f}s")
    except json.JSONDecodeError as e:
        print(f"❌ Error decoding message: {e}")
    except Exception as e:
        print(f"❌ Error handling message: {e}")

def on_error(ws, error):
    """Called when a WebSocket error occurs."""
    print(f"\n❌ WebSocket Error: {error}")
    # Attempt to signal stop on error
    stop_event.set()

def on_close(ws, close_status_code, close_msg):
    """Called when the WebSocket connection is closed."""
    print(f"\n🔌 WebSocket Disconnected: {close_status_code} - {close_msg}")

    # Ensure audio resources are released
    global stream_audio, audio
    stop_event.set()  # Signal audio thread just in case it's still running

    if stream_audio:
        if stream_audio.is_active():
            stream_audio.stop_stream()
        stream_audio.close()
        stream_audio = None
    if audio:
        audio.terminate()
        audio = None
    # Try to join the audio thread to ensure clean exit
    if audio_thread and audio_thread.is_alive():
        audio_thread.join(timeout=1.0)

# --- Main Execution ---
def run():
    global audio, stream_audio, ws_app

    print("🚀 AI Voice Agent with Groq PlayAI TTS")
    print("=" * 45)

    # Test Groq TTS connection
    try:
        print("🔍 Testing Groq PlayAI TTS connection...")
        test_audio = generate_speech_groq("Test")
        if test_audio:
            print("✅ Groq PlayAI TTS ready")
        else:
            print("❌ Groq TTS test failed")
            return
    except Exception as e:
        print(f"❌ Groq TTS error: {e}")
        print("Check your GROQ_API_KEY in .env file")
        return

    print("🎵 Using Groq PlayAI TTS (140 chars/sec, 10x faster than real-time)")

    # Initialize PyAudio
    audio = pyaudio.PyAudio()

    # Open microphone stream
    try:
        stream_audio = audio.open(
            input=True,
            frames_per_buffer=FRAMES_PER_BUFFER,
            channels=CHANNELS,
            format=FORMAT,
            rate=SAMPLE_RATE,
        )
        print("✅ Microphone stream opened")
        print("🎤 Speak into your microphone. Press Ctrl+C to stop.")
    except Exception as e:
        print(f"❌ Error opening microphone: {e}")
        if audio:
            audio.terminate()
        return  # Exit if microphone cannot be opened

    # Create WebSocketApp
    ws_app = websocket.WebSocketApp(
        API_ENDPOINT,
        header={"Authorization": YOUR_API_KEY},
        on_open=on_open,
        on_message=on_message,
        on_error=on_error,
        on_close=on_close,
    )

    # Run WebSocketApp in a separate thread to allow main thread to catch KeyboardInterrupt
    ws_thread = threading.Thread(target=ws_app.run_forever)
    ws_thread.daemon = True
    ws_thread.start()

    try:
        # Keep main thread alive until interrupted
        while ws_thread.is_alive():
            time.sleep(0.1)
    except KeyboardInterrupt:
        print("\n\n👋 Stopping AI Voice Agent...")
        stop_event.set()  # Signal audio thread to stop

        # Send termination message to the server
        if ws_app and ws_app.sock and ws_app.sock.connected:
            try:
                terminate_message = {"type": "Terminate"}
                print(f"📤 Sending termination message...")
                ws_app.send(json.dumps(terminate_message))
                # Give a moment for messages to process before forceful close
                time.sleep(1)
            except Exception as e:
                print(f"❌ Error sending termination: {e}")

        # Close the WebSocket connection (will trigger on_close)
        if ws_app:
            ws_app.close()

        # Wait for WebSocket thread to finish
        ws_thread.join(timeout=2.0)

    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        stop_event.set()
        if ws_app:
            ws_app.close()
        ws_thread.join(timeout=2.0)

    finally:
        # Final cleanup (already handled in on_close, but good as a fallback)
        if stream_audio and stream_audio.is_active():
            stream_audio.stop_stream()
        if stream_audio:
            stream_audio.close()
        if audio:
            audio.terminate()
        print("✅ Cleanup complete. Goodbye!")


if __name__ == "__main__":
    run()
