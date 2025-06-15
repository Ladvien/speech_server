#!/usr/bin/env python3
"""
Stream cloned TTS audio and play it in real-time.
"""
import requests
import pyaudio
import os
import numpy as np


def test_voice_cloning():
    base_url = "http://192.168.1.110:8000"
    audio_file_path = "voice_samples/beks_voice_sample.wav"
    # audio_file_path = "voice_samples/echos_voice_sample.wav"
    voice_name = "bek"
    test_text = "What's up you sexy hunk of man meat!?"

    # Audio playback config
    FORMAT = pyaudio.paInt16
    CHANNELS = 2  # Stereo
    RATE = 24000
    CHUNK = 2048

    def mono_to_stereo(chunk):
        mono = np.frombuffer(chunk, dtype=np.int16)
        stereo = np.repeat(mono[:, np.newaxis], CHANNELS, axis=1).flatten()
        return stereo.astype(np.int16).tobytes()

    if not os.path.exists(audio_file_path):
        print(f"❌ File not found: {audio_file_path}")
        return

    print(f"🎤 Voice name: {voice_name}")
    print(f"📝 Text: {test_text}\n")

    # Step 1: Clone voice if not already cloned
    print("📤 Checking/Cloning voice...")
    voices = requests.get(f"{base_url}/voices").json()
    if voice_name not in [v["voice_name"] for v in voices]:
        with open(audio_file_path, "rb") as f:
            files = {"audio_file": f}
            data = {
                "voice_name": voice_name,
                "description": f"Cloned from {os.path.basename(audio_file_path)}",
            }
            response = requests.post(f"{base_url}/voices/clone", files=files, data=data)
        if response.status_code != 200:
            print(f"❌ Voice cloning failed: {response.status_code}")
            print(f"   Response: {response.text}")
            return
        print("✅ Voice cloned.")
    else:
        print("✅ Voice already exists.")

    # Step 2: Request streaming synthesis
    print("\n🗣️  Requesting streaming synthesis...")
    payload = {
        "text": test_text,
        "voice_name": voice_name,
        "cfg_weight": 0.1,
        "exaggeration": 0.2,
    }

    print(f"   Payload: {payload}\n")

    response = requests.post(f"{base_url}/synthesize", json=payload, stream=True)
    if response.status_code != 200:
        print(f"❌ Streaming failed: {response.status_code}")
        print(f"   Response: {response.text}")
        return

    print("🔊 Playing streamed audio...\n")

    # Step 3: Play audio stream
    p = pyaudio.PyAudio()
    stream = p.open(format=FORMAT, channels=CHANNELS, rate=RATE, output=True)

    header_skipped = False
    for chunk in response.iter_content(chunk_size=CHUNK):
        if chunk:
            if not header_skipped:
                chunk = chunk[44:]  # skip WAV header
                header_skipped = True
            stereo = mono_to_stereo(chunk)
            stream.write(stereo)

    stream.stop_stream()
    stream.close()
    p.terminate()

    print("✅ Playback complete.\n")


if __name__ == "__main__":
    test_voice_cloning()
