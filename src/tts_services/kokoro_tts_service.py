import os
import io
import re
import uuid
import requests
import soundfile as sf
from typing import AsyncGenerator, Optional, Tuple, Dict, List
from fastapi import HTTPException, UploadFile
from dataclasses import dataclass, field
from kokoro_onnx import Kokoro
import logging
from fastapi.responses import StreamingResponse
import numpy as np


from speech_server.common.base_tts_config import TTSBaseConfig
from speech_server.common.base_tts_service import TTSService


@dataclass
class KokoroPipelineConfig:
    voice: str
    speed: float
    language_code: str


@dataclass
class KokoroResponseConfig:
    format: str
    sample_rate: int
    channels: int


@dataclass
class KokoroTTSServiceConfig:
    # Required fields first
    pipeline: KokoroPipelineConfig
    response: KokoroResponseConfig

    voices_name: str = "voices-v1.0.bin"
    model_name: str = "kokoro-v1.0.onnx"

    # Optional/defaults below
    runtime_data_dir: str = field(
        default_factory=lambda: os.path.abspath("runtime_data")
    )
    default_voice: str = "default"
    sample_rate: int = 24000
    supported_formats: List[str] = field(default_factory=lambda: ["wav"])

    base_download_link: str = (
        "https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.0"
    )
    model_filenames: List[str] = field(
        default_factory=lambda: [
            "kokoro-v1.0.fp16-gpu.onnx",
            "kokoro-v1.0.fp16.onnx",
            "kokoro-v1.0.int8.onnx",
            "kokoro-v1.0.onnx",
        ]
    )
    voices_filenames: List[str] = field(default_factory=lambda: ["voices-v1.0.bin"])
    output_temp_dir: Optional[str] = None


class KokoroTTSService(TTSService):
    def __init__(self, config: KokoroTTSServiceConfig):
        super().__init__()
        self.config = config
        self.model = None
        self.default_voice = config.pipeline.voice
        self.supported_formats = [config.response.format]
        self.start_time = None

        # Ensure runtime directory exists
        os.makedirs(self.config.runtime_data_dir, exist_ok=True)

        # Track audio file paths
        self.audio_files: Dict[str, str] = {}

    def _get_runtime_path(self, filename: str) -> str:
        return os.path.join(self.config.runtime_data_dir, filename)

    async def initialize(self):
        # Ensure model + voice files exist, try downloading them
        for local_basename, remote_candidates in [
            (self.config.model_name, self.config.model_filenames),
            (self.config.voices_name, self.config.voices_filenames),
        ]:
            local_path = self._get_runtime_path(local_basename)
            if not os.path.exists(local_path):
                os.makedirs(os.path.dirname(local_path), exist_ok=True)
                for candidate in remote_candidates:
                    url = f"{self.config.base_download_link}/{candidate}"
                    logging.info(f"Attempting download from {url}")
                    try:
                        resp = requests.get(url, allow_redirects=True)
                        if resp.ok and "html" not in resp.headers.get(
                            "Content-Type", ""
                        ):
                            with open(local_path, "wb") as f:
                                f.write(resp.content)
                            logging.info(f"✅ Downloaded and saved to {local_path}")
                            break
                    except Exception as e:
                        logging.warning(f"❌ Failed to download {candidate}: {e}")
                else:
                    raise RuntimeError(
                        f"❌ Failed to download {local_basename} from any known source."
                    )

        self.model = Kokoro(
            model_path=self._get_runtime_path(self.config.model_name),
            voices_path=self._get_runtime_path(self.config.voices_name),
        )
        self.is_initialized = True

    async def is_ready(self) -> bool:
        return self.model is not None

    async def get_available_voices(self) -> List[Dict[str, str]]:
        return [{"name": name} for name in self.model.get_voices()]

    def synthesize_stream(
        self,
        text: str,
        voice_name: str,
        audio_prompt_path: str = None,
        exaggeration: float = 1.0,
        cfg_weight: float = 1.0,
        output_format: str = "wav",
    ):
        sample, sample_rate = self.model.create(
            text=text,
            voice=voice_name,
            speed=self.config.pipeline.speed,
            lang=self.config.pipeline.language_code,
            is_phonemes=False,
            trim=True,
        )

        if sample is None or len(sample) == 0:
            raise RuntimeError("Kokoro TTS returned empty audio.")

        buffer = io.BytesIO()
        fmt = output_format.upper()
        if fmt == "WAV":
            sf.write(buffer, sample, samplerate=sample_rate, format=fmt)
        else:
            raise ValueError(f"Unsupported output format: {fmt}")

        buffer.seek(0)

        def stream_audio():
            while True:
                chunk = buffer.read(4096)
                if not chunk:
                    break
                yield chunk

        return stream_audio()

    async def synthesize(
        self,
        text: str,
        voice_name: Optional[str] = None,
        audio_prompt_path: Optional[str] = None,
        exaggeration: float = 0.5,
        cfg_weight: float = 0.5,
        output_format: str = "wav",
    ) -> Tuple[str, float]:
        stream = await self.synthesize_stream(
            text=text,
            voice_name=voice_name,
            output_format=output_format,
        )
        file_id = str(uuid.uuid4())
        file_path = os.path.join(
            self.config.runtime_data_dir, f"{file_id}.{output_format}"
        )
        total_duration = 0.0

        with sf.SoundFile(
            file_path,
            mode="w",
            samplerate=self.config.response.sample_rate,
            channels=self.config.response.channels,
            format=self.config.response.format.upper(),
        ) as out_f:
            async for chunk in stream:
                audio_data, sr = sf.read(io.BytesIO(chunk))
                total_duration += len(audio_data) / sr
                out_f.write(audio_data)

        self.audio_files[file_id] = file_path
        return file_id, total_duration

    async def get_audio_file(self, file_id: str) -> Optional[str]:
        return self.audio_files.get(file_id)

    async def delete_audio_file(self, file_id: str) -> bool:
        path = self.audio_files.pop(file_id, None)
        if path and os.path.exists(path):
            os.remove(path)
            return True
        return False

    async def clone_voice(
        self, voice_name: str, audio_file: UploadFile, description: Optional[str] = None
    ) -> Dict:
        raise NotImplementedError("Kokoro ONNX model does not support voice cloning")

    async def delete_cloned_voice(self, voice_name: str) -> bool:
        return False

    async def get_voice_sample_file(self, voice_name: str) -> Optional[str]:
        return None

    async def cleanup(self):
        self.model = None
        self.audio_files.clear()
