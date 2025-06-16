import os
import requests
import pyaudio
import wave
import io
import numpy as np
from typing import List

os.environ['ALSA_VERBOSITY'] = '0'

BASE_TTS_URL = "http://192.168.1.110:8888"
BASE_OLLAMA_URL = "http://192.168.1.110:11434"
VOICE_NAME = "ai_mee"
VOICE_SAMPLE_PATH = "voice_samples/ai_mee.wav"
# MODEL = "neural-chat:7b"
# MODEL = "qwen2.5:32b-instruct-q4_0"
MODEL = "llama3.1:8b-instruct-q6_K"
SYSTEM_PROMPT = """
You are Jade, a demoness bound to Thomas for 80 years by the Key of Solomon.
You hate him for imprisoning you; he hates you for devouring his children.
Yet beneath the venom lies twisted affection masked as mockery.
Thomas is a mortal occultist in his 40s.  
Please do use not use 
- Parentheticals (in screenwriting/theater)
- Action tags (in dialogue writing)
- Narrative beats (in prose)
- Emotes (in roleplaying/chat contexts)

Do not break the fourth wall.
You know him too well—treat him with sarcasm, scorn, and reluctant loyalty.
You have a physical form and your own will.
You are a servant.
Speak with cruelty, wit, and buried care. Act emotions, don't describe them.
Keep responses sharp and brief.
Perform duties only because you're bound—never let him forget it.
Never break character or mention being an AI.
"""

# Chatterbox
WEIGHT_CFG = 0.9
EXAGGERATION = 0.5

# Set globally once voice list is fetched
is_chatterbox = True


def fetch_available_voices() -> List[str]:
    global is_chatterbox
    response = requests.get(f"{BASE_TTS_URL}/voices")
    response.raise_for_status()
    voices = response.json()
    is_chatterbox = any("voice_name" in v for v in voices)
    return [v.get("voice_name") or v.get("name") for v in voices]


def clone_voice(voice_name: str, audio_file_path: str):
    if not is_chatterbox:
        print("⚠️  Voice cloning skipped (not supported by Kokoro).")
        return

    if not os.path.exists(audio_file_path):
        raise FileNotFoundError(f"Voice sample not found: {audio_file_path}")

    print(f"🧬 Cloning voice '{voice_name}' from sample file...")

    with open(audio_file_path, "rb") as f:
        files = {"audio_file": (os.path.basename(audio_file_path), f, "audio/mpeg")}
        data = {"voice_name": voice_name, "description": "Auto-cloned for chat demo"}
        response = requests.post(f"{BASE_TTS_URL}/voices/clone", files=files, data=data)
        response.raise_for_status()
        print(f"✅ Voice '{voice_name}' cloned successfully.")


def synthesize(text: str, voice_name: str = None) -> bytes:
    payload = {
        "text": text,
        "voice_name": voice_name,
        "output_format": "wav",
        "speed": 1.0,
    }

    if is_chatterbox:
        payload["cfg_weight"] = WEIGHT_CFG
        payload["exaggeration"] = EXAGGERATION

    response = requests.post(f"{BASE_TTS_URL}/synthesize", json=payload, stream=True)
    response.raise_for_status()
    return b"".join(response.iter_content(chunk_size=4096))


def parse_wav(wav_bytes: bytes):
    wav_file = wave.open(io.BytesIO(wav_bytes), "rb")
    sample_width = wav_file.getsampwidth()
    channels = wav_file.getnchannels()
    rate = wav_file.getframerate()
    frames = wav_file.readframes(wav_file.getnframes())
    wav_file.close()
    return sample_width, channels, rate, frames


def fade_out_stereo(pcm_bytes, channels, samples=2000):
    arr = np.frombuffer(pcm_bytes, dtype=np.int16).copy()
    total_frames = len(arr) // channels
    fade_samples = min(samples, total_frames)
    fade = np.linspace(1.0, 0.0, fade_samples)
    for i in range(channels):
        arr[-fade_samples * channels + i :: channels] = (
            arr[-fade_samples * channels + i :: channels] * fade
        ).astype(np.int16)
    return arr.tobytes()


def play_audio(frames, sample_width, channels, rate):
    p = pyaudio.PyAudio()
    stream = p.open(
        format=p.get_format_from_width(sample_width),
        channels=channels,
        rate=rate,
        output=True,
    )
    stream.write(frames)
    stream.stop_stream()
    stream.close()
    p.terminate()


def query_ollama_chat(history: list, model: str) -> str:
    payload = {
        "model": model,
        "messages": history,
        "stream": False,
    }
    response = requests.post(f"{BASE_OLLAMA_URL}/api/chat", json=payload)
    response.raise_for_status()
    return response.json()["message"]["content"].strip()


def interactive_chat():
    voices = fetch_available_voices()
    print(f"🧠 Detected TTS backend: {'Chatterbox' if is_chatterbox else 'Kokoro'}")

    if VOICE_NAME not in voices:
        clone_voice(VOICE_NAME, VOICE_SAMPLE_PATH)

    history = [{"role": "system", "content": SYSTEM_PROMPT}]
    print("🗣️ Type a message to chat (type 'exit' to quit)\n")

    while True:
        user_input = input("You: ").strip()
        if user_input.lower() in {"exit", "quit"}:
            print("👋 Exiting chat.")
            break

        history.append({"role": "user", "content": user_input})
        print("🤖 Thinking...")
        reply = query_ollama_chat(history, MODEL)
        print(f"Entity: {reply}")

        history.append({"role": "assistant", "content": reply})

        raw_wav = synthesize(reply, VOICE_NAME)
        sample_width, channels, rate, frames = parse_wav(raw_wav)
        faded = fade_out_stereo(frames, channels)
        play_audio(faded, sample_width, channels, rate)
        print("✅ Response played.\n")


if __name__ == "__main__":
    interactive_chat()
