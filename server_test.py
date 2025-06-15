import requests
import pyaudio
import wave
import io
import numpy as np


def test_voice_cloning():
    base_url = "http://192.168.1.110:8000"
    voice_name = "ai_mee"
    audio_file_path = "voice_samples/063847_french-female-voice-44607.wav"
    test_text = """
Well, then.  Long, long ago there were a pair of homely women who tended to the 
ships of the northern fleet.  The right ugliest women you have ever seen.  Stick with me, please.
    """

    test_text = """
    So, these women had no one who would love them.  As they were renowned for their ugly faces.
    And as such, no one ever courted them or fluffed their pantaloons.
    """

    test_text = """
No, sadly, there was no sucking, mon chéri.  
"""

    test_text = """
They just existed alone, two homely, ugly women, devoid of a loving destiny.  Truly... wretched.
"""

    test_text = """
The end.  The very, very sad, end.  Good night.
"""

    # Request voice clone if needed
    voices = requests.get(f"{base_url}/voices").json()
    if voice_name not in [v["voice_name"] for v in voices]:
        with open(audio_file_path, "rb") as f:
            files = {"audio_file": f}
            data = {"voice_name": voice_name, "description": "Cloned sample"}
            r = requests.post(f"{base_url}/voices/clone", files=files, data=data)
            r.raise_for_status()

    # Request synthesized TTS stream
    payload = {
        "text": test_text,
        "voice_name": voice_name,
        "cfg_weight": 0.05,
        "exaggeration": 0.025,
    }
    response = requests.post(f"{base_url}/synthesize", json=payload, stream=True)
    response.raise_for_status()

    # Buffer the entire response into memory
    raw_audio = b"".join(response.iter_content(chunk_size=4096))

    # Decode with wave module to ensure correct format
    wav_file = wave.open(io.BytesIO(raw_audio), "rb")

    sample_width = wav_file.getsampwidth()
    channels = wav_file.getnchannels()
    rate = wav_file.getframerate()
    frames = wav_file.readframes(wav_file.getnframes())

    print(f"🎧 Audio Format: {channels}ch, {rate}Hz, {sample_width*8}-bit")

    # Optional: fade-out the last N samples
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

    frames = fade_out_stereo(frames)

    # Playback
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

    print("✅ Playback complete.")


if __name__ == "__main__":
    test_voice_cloning()
