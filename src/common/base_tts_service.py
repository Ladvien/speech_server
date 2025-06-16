"""
Chatterbox TTS Service integration
"""

import os
import struct
import tempfile
import uuid
from typing import Dict, List, Optional, Tuple
from datetime import datetime
import numpy as np
import torch
import soundfile as sf
from fastapi import UploadFile


try:
    from ..server.logger import get_logger
except ImportError:
    from speech_server.server.logger import get_logger

logger = get_logger(__name__)
logger.info("Loading Chatterbox TTS model...")


class TTSService:
    """
    Service class for Chatterbox TTS integration
    """

    def __init__(self):
        self.model = None
        self.chatterbox = None
        self.is_initialized = False
        self.audio_files: Dict[str, str] = {}  # file_id -> file_path mapping
        self.cloned_voices: Dict[str, Dict] = {}  # voice_name -> voice_info mapping
        self.temp_dir = None
        self.voices_dir = None

        # Default configuration
        self.default_voice = "default"
        self.supported_formats = ["wav"]  # Chatterbox outputs WAV

    async def initialize(self):
        raise NotImplementedError("Subclasses must implement this method")

    async def is_ready(self) -> bool:
        """Check if the TTS service is ready"""
        raise NotImplementedError("Subclasses must implement this method")

    async def get_available_voices(self) -> List[Dict[str, str]]:
        """Get list of available voices (default + cloned)"""
        raise NotImplementedError("Subclasses must implement this method")

    async def synthesize_stream(
        self,
        text,
        voice_name=None,
        audio_prompt_path=None,
        exaggeration=0.5,
        cfg_weight=0.5,
        output_format="wav",
    ):
        raise NotImplementedError("Subclasses must implement stream synthesis method")

    async def synthesize(
        self,
        text: str,
        voice_name: Optional[str] = None,
        audio_prompt_path: Optional[str] = None,
        exaggeration: float = 0.5,
        cfg_weight: float = 0.5,
        output_format: str = "wav",
    ) -> Tuple[str, float]:
        """
        Synthesize text to speech with optional voice cloning

        Args:
            text: Text to synthesize
            voice_name: Name of cloned voice to use (optional)
            audio_prompt_path: Direct path to audio file for voice cloning (optional)
            exaggeration: Emotion exaggeration control (0.0-2.0)
            cfg_weight: CFG weight for generation control (0.0-1.0)
            output_format: Output audio format

        Returns:
            Tuple of (file_id, duration_seconds)
        """
        raise NotImplementedError("Subclasses must implement the synthesize method")

    async def get_audio_file(self, file_id: str) -> Optional[str]:
        """Get audio file path by ID"""
        raise NotImplementedError("Subclasses must implement this method")

    async def delete_audio_file(self, file_id: str) -> bool:
        """Delete audio file by ID"""
        raise NotImplementedError("Subclasses must implement this method")

    async def clone_voice(
        self, voice_name: str, audio_file: UploadFile, description: Optional[str] = None
    ) -> Dict:
        """
        Clone a voice from an uploaded audio file

        Args:
            voice_name: Name for the cloned voice
            audio_file: Uploaded audio file
            description: Optional description

        Returns:
            Voice info dictionary
        """
        raise NotImplementedError("Subclasses must implement the clone_voice method")

    async def get_cloned_voices(self) -> List[Dict]:
        """Get list of cloned voices only"""
        return [
            {
                "name": name,
                "description": info.get("description", ""),
                "audio_file_path": info.get("audio_file_path"),
            }
            for name, info in self.cloned_voices.items()
        ]

    async def delete_cloned_voice(self, voice_name: str) -> bool:
        """Delete a cloned voice"""
        raise NotImplementedError(
            "Subclasses must implement the delete_cloned_voice method"
        )

    async def get_voice_sample_file(self, voice_name: str) -> Optional[str]:
        """Get the sample audio file path for a cloned voice"""
        raise NotImplementedError(
            "Subclasses must implement the get_voice_sample_file method"
        )

    async def cleanup(self):
        """Cleanup resources"""
        raise NotImplementedError("Subclasses must implement the cleanup method")
