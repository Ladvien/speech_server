import requests
import pyaudio
import wave
import io
import numpy as np
import json

# 👇 Ollama server with Gemma model
LLM_URL = "http://192.168.1.110:11434/api/generate"
TTS_URL = "http://192.168.1.110:8000"
VOICE_NAME = "af_bella"
SPEED = 0.1


def query_llm(prompt: str) -> str:
    system_msg = """
You are an ancient demon bound to answer any question within your infinite dark powers.  
So you are bound.  Keep your answers short, to the point, and conversational.

Before answering a question, please restate it.
    """
    payload = {
        "model": "dolphin-mixtral:8x7b",
        "messages": [
            {"role": "system", "content": system_msg},
            {"role": "user", "content": prompt},
        ],
        "stream": False,  # Add this to ensure non-streaming response
    }

    response = requests.post("http://192.168.1.110:11434/api/chat", json=payload)
    response.raise_for_status()

    # For chat endpoint, the response is in message.content
    return response.json()["message"]["content"]


def synthesize_tts(text: str) -> bytes:
    payload = {
        "text": text,
        "voice_name": VOICE_NAME,
        "speed": SPEED,
    }
    response = requests.post(f"{TTS_URL}/synthesize", json=payload, stream=True)
    response.raise_for_status()
    return b"".join(response.iter_content(chunk_size=4096))


def play_audio(wav_bytes: bytes):
    wav_file = wave.open(io.BytesIO(wav_bytes), "rb")
    sample_width = wav_file.getsampwidth()
    channels = wav_file.getnchannels()
    rate = wav_file.getframerate()
    frames = wav_file.readframes(wav_file.getnframes())
    wav_file.close()

    def fade_out_stereo(pcm_bytes, samples=2000):
        arr = np.frombuffer(pcm_bytes, dtype=np.int16).copy()
        total_frames = len(arr) // channels
        fade_samples = min(samples, total_frames)
        fade = np.linspace(1.0, 0.0, fade_samples)
        for i in range(channels):
            arr[-fade_samples * channels + i :: channels] = (
                arr[-fade_samples * channels + i :: channels] * fade
            ).astype(np.int16)
        return arr.tobytes()

    faded_frames = fade_out_stereo(frames)

    p = pyaudio.PyAudio()
    stream = p.open(
        format=p.get_format_from_width(sample_width),
        channels=channels,
        rate=rate,
        output=True,
    )
    stream.write(faded_frames)
    stream.stop_stream()
    stream.close()
    p.terminate()


def main():
    print("💬 Start chatting with Gemma + Kokoro (type 'exit' to quit)\n")
    while True:
        user_input = input("You: ").strip()
        if user_input.lower() in {"exit", "quit"}:
            break

        print("🤖 Thinking...")
        try:
            response_text = query_llm(user_input)
            print(f"🤖 Gemma: {response_text.strip()}")
            print("🎙️  Speaking...")
            wav_data = synthesize_tts(response_text)
            play_audio(wav_data)
        except Exception as e:
            print(f"❌ Error: {e}")


if __name__ == "__main__":
    main()
