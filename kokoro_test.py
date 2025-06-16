import requests
import pyaudio
import wave
import io
import numpy as np


def test_kokoro_tts():
    base_url = "http://192.168.1.110:8000"
    voice_name = "af_bella"  # must be one of the built-in Kokoro voices

    test_text = """
This is almost real time  talking.
"""

    # ✅ Confirm voice exists
    voices = requests.get(f"{base_url}/voices").json()
    voice_names = [v.get("name") or v.get("voice_name") for v in voices]
    if voice_name not in voice_names:
        raise ValueError(f"Voice '{voice_name}' not available in Kokoro engine.")

    # ✅ Request synthesis
    payload = {
        "text": test_text,
        "voice_name": voice_name,
        "speed": 0.1,
    }
    response = requests.post(f"{base_url}/synthesize", json=payload, stream=True)
    response.raise_for_status()

    # ✅ Buffer the full WAV stream into memory
    raw_audio = b"".join(response.iter_content(chunk_size=4096))

    # ✅ Parse WAV header
    wav_file = wave.open(io.BytesIO(raw_audio), "rb")
    sample_width = wav_file.getsampwidth()
    channels = wav_file.getnchannels()
    rate = wav_file.getframerate()
    frames = wav_file.readframes(wav_file.getnframes())
    wav_file.close()

    print(f"🎧 Format: {channels}ch, {rate}Hz, {sample_width * 8}-bit")

    # ✅ Optional fade-out
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

    # ✅ Playback
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

    print("✅ Playback complete.")


if __name__ == "__main__":
    test_kokoro_tts()
