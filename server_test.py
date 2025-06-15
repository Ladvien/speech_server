import requests
import pyaudio
import numpy as np
from scipy.signal import resample

# Settings
TTS_URL = "http://localhost:8000/synthesize"
TEXT = "Hello! This is Chatterbox, streaming on Linux."
INPUT_RATE = 24000
OUTPUT_RATE = 44100
CHANNELS = 2
CHUNK = 2048

# Request payload
payload = {"text": TEXT, "output_format": "wav"}

# Init PyAudio
p = pyaudio.PyAudio()

# Pick working output device
print("🔎 Available output devices:")
for i in range(p.get_device_count()):
    info = p.get_device_info_by_index(i)
    if info["maxOutputChannels"] > 0:
        print(f"{i}: {info['name']} (Channels: {info['maxOutputChannels']})")

# OPTIONAL: Choose correct device index manually
output_device_index = None  # or something like 7 for pipewire

# Start streaming
try:
    print("🔊 Connecting and streaming TTS audio...")
    response = requests.post(TTS_URL, json=payload, stream=True)
    response.raise_for_status()

    stream = p.open(
        format=pyaudio.paInt16,
        channels=CHANNELS,
        rate=OUTPUT_RATE,
        output=True,
        output_device_index=output_device_index,
    )

    header_skipped = False
    for chunk in response.iter_content(chunk_size=CHUNK):
        if not chunk:
            continue
        if not header_skipped:
            chunk = chunk[44:]  # skip WAV header
            header_skipped = True

        # Mono int16 array
        mono = np.frombuffer(chunk, dtype=np.int16)

        # Resample to 44.1kHz
        resampled = resample(mono, int(len(mono) * OUTPUT_RATE / INPUT_RATE))

        # Stereo
        stereo = (
            np.repeat(resampled[:, np.newaxis], CHANNELS, axis=1)
            .flatten()
            .astype(np.int16)
        )

        stream.write(stereo.tobytes())

    stream.stop_stream()
    stream.close()
    print("✅ Playback complete.")
except Exception as e:
    print(f"❌ Error: {e}")
finally:
    p.terminate()
