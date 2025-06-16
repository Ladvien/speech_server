from typing import Optional, Dict, Tuple, List
from fastapi import UploadFile
import numpy as np
import os
import uuid
import struct
import soundfile as sf
import torch
from datetime import datetime
from dataclasses import dataclass, field

from chatterbox.tts import ChatterboxTTS
from speech_server.common.base_tts_config import TTSBaseConfig

try:
    from ..server.logger import get_logger
except ImportError:
    from server.logger import get_logger

logger = get_logger(__name__)


@dataclass
class ChatterboxPipelineConfig:
    exaggeration: float = 0.5
    cfg_weight: float = 0.5


@dataclass
class ChatterboxResponseConfig:
    format: str = "wav"
    sample_rate: int = 24000
    channels: int = 1


@dataclass
class ChatterboxTTSServiceConfig(TTSBaseConfig):
    pipeline: ChatterboxPipelineConfig = field(default_factory=ChatterboxPipelineConfig)
    response: ChatterboxResponseConfig = field(default_factory=ChatterboxResponseConfig)


class ChatterboxTTSService:
    def __init__(self, config: ChatterboxTTSServiceConfig):
        self.config = config
        self.model = None
        self.chatterbox = None
        self.is_initialized = False

        self.audio_files: Dict[str, str] = {}
        self.cloned_voices: Dict[str, Dict] = {}

        self.temp_dir = os.path.join(self.config.runtime_data_dir, "chatterbox_tmp")
        self.voices_dir = os.path.join(self.temp_dir, "voices")
        os.makedirs(self.voices_dir, exist_ok=True)

    async def initialize(self):
        logger.info("Initializing Chatterbox TTS...")
        await self._initialize_model()
        self.is_initialized = True
        logger.info("Chatterbox TTS initialized")

    async def _initialize_model(self):
        device = (
            "cuda"
            if torch.cuda.is_available()
            else "mps" if torch.backends.mps.is_available() else "cpu"
        )
        logger.info(f"Using device: {device}")
        self.chatterbox = ChatterboxTTS.from_pretrained(device=device)
        self.model = {
            "status": "loaded",
            "voices": [self.config.default_voice],
            "sample_rate": self.config.sample_rate,
        }

    async def is_ready(self) -> bool:
        return self.is_initialized and self.model is not None

    async def get_available_voices(self) -> List[Dict[str, str]]:
        voices = [
            {
                "voice_name": self.config.default_voice,
                "description": "Default Chatterbox voice",
                "is_cloned": False,
                "created_at": None,
            }
        ]
        for name, info in self.cloned_voices.items():
            voices.append(
                {
                    "voice_name": name,
                    "description": info.get("description", "Cloned voice"),
                    "audio_file_path": info.get("audio_file_path"),
                    "is_cloned": True,
                    "created_at": info.get("created_at"),
                }
            )
        return voices

    async def synthesize_stream(
        self,
        text,
        voice_name=None,
        audio_prompt_path=None,
        exaggeration=None,
        cfg_weight=None,
        output_format="wav",
    ):
        exaggeration = exaggeration or self.config.pipeline.exaggeration
        cfg_weight = cfg_weight or self.config.pipeline.cfg_weight

        prompt_path = audio_prompt_path or self.cloned_voices.get(voice_name, {}).get(
            "audio_file_path"
        )
        audio_data, sr = await self._synthesize_audio(
            text, prompt_path, exaggeration, cfg_weight
        )
        pcm_audio = (audio_data * 32767).astype(np.int16).tobytes()
        data_size = len(pcm_audio)
        wav_header = struct.pack(
            "<4sI4s4sIHHIIHH4sI",
            b"RIFF",
            36 + data_size,
            b"WAVE",
            b"fmt ",
            16,
            1,
            1,
            sr,
            sr * 2,
            2,
            16,
            b"data",
            data_size,
        )
        yield wav_header
        chunk_size = sr
        for i in range(0, len(pcm_audio), chunk_size):
            yield pcm_audio[i : i + chunk_size]

    async def synthesize(
        self,
        text,
        voice_name=None,
        audio_prompt_path=None,
        exaggeration=None,
        cfg_weight=None,
        output_format="wav",
    ) -> Tuple[str, float]:
        if not await self.is_ready():
            raise RuntimeError("TTS not initialized")
        if output_format not in self.config.supported_formats:
            raise ValueError(f"Unsupported format: {output_format}")

        exaggeration = exaggeration or self.config.pipeline.exaggeration
        cfg_weight = cfg_weight or self.config.pipeline.cfg_weight

        file_id = str(uuid.uuid4())
        prompt_path = audio_prompt_path or self.cloned_voices.get(voice_name, {}).get(
            "audio_file_path"
        )
        audio_data, sr = await self._synthesize_audio(
            text, prompt_path, exaggeration, cfg_weight
        )
        file_path = await self._save_audio_file(file_id, audio_data, sr, output_format)
        self.audio_files[file_id] = file_path
        return file_id, len(audio_data) / sr

    async def _synthesize_audio(
        self,
        text: str,
        audio_prompt_path: Optional[str],
        exaggeration: float,
        cfg_weight: float,
    ) -> Tuple[np.ndarray, int]:
        if audio_prompt_path and os.path.exists(audio_prompt_path):
            logger.info(f"Generating audio (prompt={audio_prompt_path})...")
            audio_tensor = self.chatterbox.generate(
                text=text,
                audio_prompt_path=audio_prompt_path,
                exaggeration=exaggeration,
                cfg_weight=cfg_weight,
            )
            logger.info("Audio generation complete.")

        else:
            logger.info(f"Generating audio (prompt={audio_prompt_path})...")
            audio_tensor = self.chatterbox.generate(
                text=text,
                exaggeration=exaggeration,
                cfg_weight=cfg_weight,
            )
            logger.info("Audio generation complete.")

        audio_data = (
            audio_tensor.cpu().numpy()
            if hasattr(audio_tensor, "cpu")
            else np.array(audio_tensor)
        )
        return audio_data.squeeze().astype(np.float32), self.chatterbox.sr

    async def _save_audio_file(
        self, file_id: str, audio_data: np.ndarray, sample_rate: int, format: str
    ) -> str:
        path = os.path.join(self.temp_dir, f"{file_id}.{format}")
        sf.write(path, audio_data, sample_rate, format=format.upper())
        return path

    async def get_audio_file(self, file_id: str) -> Optional[str]:
        return self.audio_files.get(file_id)

    async def delete_audio_file(self, file_id: str) -> bool:
        path = self.audio_files.get(file_id)
        if path and os.path.exists(path):
            os.remove(path)
            del self.audio_files[file_id]
            return True
        return False

    async def clone_voice(
        self, voice_name: str, audio_file: UploadFile, description: Optional[str] = None
    ) -> Dict:
        if voice_name in self.cloned_voices:
            raise ValueError(f"Voice '{voice_name}' already exists")
        path = os.path.join(self.voices_dir, f"{voice_name}.wav")
        with open(path, "wb") as f:
            f.write(await audio_file.read())
        try:
            data, sr = sf.read(path)
            sf.write(path, data, sr, format="WAV")
        except Exception:
            pass
        info = {
            "voice_name": voice_name,
            "description": description or f"Cloned from {audio_file.filename}",
            "audio_file_path": path,
            "is_cloned": True,
            "created_at": datetime.now().isoformat(),
        }
        self.cloned_voices[voice_name] = info
        return info

    async def delete_cloned_voice(self, voice_name: str) -> bool:
        voice = self.cloned_voices.get(voice_name)
        if not voice:
            return False
        path = voice.get("audio_file_path")
        if path and os.path.exists(path):
            os.remove(path)
        del self.cloned_voices[voice_name]
        return True

    async def cleanup(self):
        import shutil

        for file_id in list(self.audio_files):
            await self.delete_audio_file(file_id)
        for voice_name in list(self.cloned_voices):
            await self.delete_cloned_voice(voice_name)
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)
        self.is_initialized = False
