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

# Import Chatterbox TTS with correct import
from chatterbox.tts import ChatterboxTTS
import torch


try:
    from .logger import get_logger
except ImportError:
    # Handle direct execution
    from logger import get_logger

logger = get_logger(__name__)
logger.info("Loading Chatterbox TTS model...")


class ChatterboxTTSService:
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
        """Initialize the TTS model"""
        try:
            logger.info("Initializing Chatterbox TTS service...")

            # Create temporary directory for audio files
            self.temp_dir = tempfile.mkdtemp(prefix="chatterbox_tts_")
            logger.info(f"Created temp directory: {self.temp_dir}")

            # Create directory for voice samples
            self.voices_dir = os.path.join(self.temp_dir, "voices")
            os.makedirs(self.voices_dir, exist_ok=True)
            logger.info(f"Created voices directory: {self.voices_dir}")

            # Initialize the TTS pipeline
            await self._initialize_model()

            self.is_initialized = True
            logger.info("Chatterbox TTS service initialized successfully")

        except Exception as e:
            logger.error(f"Failed to initialize TTS service: {e}")
            raise

    async def _initialize_model(self):
        """Initialize the actual TTS model"""
        try:
            if torch.cuda.is_available():
                device = "cuda"
            elif torch.backends.mps.is_available():
                device = "mps"
            else:
                device = "cpu"

            logger.info(f"Using device: {device}")

            self.chatterbox = ChatterboxTTS.from_pretrained(device=device)
            logger.info("Chatterbox TTS model loaded successfully")

            self.model = {
                "status": "loaded",
                "voices": [
                    "default"
                ],  # Chatterbox uses voice cloning, not predefined voices
                "sample_rate": 24000,  # Chatterbox uses 24kHz
            }

        except ImportError as e:
            logger.error(f"Chatterbox TTS not installed: {e}")
            logger.error("Install with: pip install chatterbox-tts")
            raise RuntimeError("Chatterbox TTS is required but not installed")
        except Exception as e:
            logger.error(f"Failed to load Chatterbox TTS: {e}")
            raise

    async def is_ready(self) -> bool:
        """Check if the TTS service is ready"""
        return self.is_initialized and self.model is not None

    async def get_available_voices(self) -> List[Dict[str, str]]:
        """Get list of available voices (default + cloned)"""
        if not await self.is_ready():
            raise RuntimeError("TTS service not initialized")

        voices = [
            {
                "voice_name": "default",
                "description": "Default Chatterbox voice",
                "is_cloned": False,
                "created_at": None,
            }
        ]

        # Add cloned voices
        for voice_name, voice_info in self.cloned_voices.items():
            voices.append(
                {
                    "voice_name": voice_name,
                    "description": voice_info.get("description", "Cloned voice"),
                    "audio_file_path": voice_info.get("audio_file_path"),
                    "is_cloned": True,
                    "created_at": voice_info.get("created_at"),
                }
            )

        return voices

    async def synthesize_stream(
        self,
        text,
        voice_name=None,
        audio_prompt_path=None,
        exaggeration=0.5,
        cfg_weight=0.5,
        output_format="wav",
    ):
        # Determine actual audio prompt path
        final_audio_prompt_path = None

        if audio_prompt_path:
            final_audio_prompt_path = audio_prompt_path
        elif voice_name and voice_name in self.cloned_voices:
            final_audio_prompt_path = self.cloned_voices[voice_name]["audio_file_path"]
            logger.info(f"Using cloned voice '{voice_name}' in streaming synthesis")

        audio_data, sample_rate = await self._synthesize_audio(
            text, final_audio_prompt_path, exaggeration, cfg_weight
        )

        # Convert float32 audio to PCM 16-bit
        pcm_audio = (audio_data * 32767).astype(np.int16).tobytes()

        # Build a WAV header (mono, 16-bit)
        num_samples = len(pcm_audio) // 2
        data_size = num_samples * 2
        wav_header = struct.pack(
            "<4sI4s4sIHHIIHH4sI",
            b"RIFF",
            36 + data_size,
            b"WAVE",
            b"fmt ",
            16,
            1,
            1,
            sample_rate,
            sample_rate * 2,
            2,
            16,
            b"data",
            data_size,
        )

        yield wav_header

        # Yield in small chunks (~0.5s)
        chunk_size = sample_rate * 2 // 2
        for i in range(0, len(pcm_audio), chunk_size):
            yield pcm_audio[i : i + chunk_size]

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
            speed: Speech speed multiplier (not used by Chatterbox directly)
            exaggeration: Emotion exaggeration control (0.0-2.0)
            cfg_weight: CFG weight for generation control (0.0-1.0)
            output_format: Output audio format

        Returns:
            Tuple of (file_id, duration_seconds)
        """
        if not await self.is_ready():
            raise RuntimeError("TTS service not initialized")

        if output_format not in self.supported_formats:
            raise ValueError(f"Unsupported format: {output_format}")

        try:
            # Generate unique file ID
            file_id = str(uuid.uuid4())

            # Determine audio prompt path
            final_audio_prompt_path = None

            if audio_prompt_path:
                # Use provided audio prompt path directly
                final_audio_prompt_path = audio_prompt_path
            elif voice_name and voice_name in self.cloned_voices:
                # Use cloned voice
                final_audio_prompt_path = self.cloned_voices[voice_name][
                    "audio_file_path"
                ]
                logger.info(f"Using cloned voice '{voice_name}'")
            elif voice_name and voice_name != "default":
                logger.warning(f"Voice '{voice_name}' not found, using default")

            logger.info(
                f"Synthesizing with exaggeration={exaggeration}, cfg_weight={cfg_weight}"
            )

            # Perform TTS synthesis
            audio_data, sample_rate = await self._synthesize_audio(
                text, final_audio_prompt_path, exaggeration, cfg_weight
            )

            # Save audio file
            file_path = await self._save_audio_file(
                file_id, audio_data, sample_rate, output_format
            )

            # Calculate duration
            duration = len(audio_data) / sample_rate

            # Store file mapping
            self.audio_files[file_id] = file_path

            logger.info(f"Synthesis completed: {file_id} ({duration:.2f}s)")

            return file_id, duration

        except Exception as e:
            logger.error(f"Synthesis failed: {e}")
            raise

    async def _synthesize_audio(
        self,
        text: str,
        audio_prompt_path: Optional[str],
        exaggeration: float,
        cfg_weight: float,
    ) -> Tuple[np.ndarray, int]:
        """
        Perform the actual TTS synthesis using Chatterbox
        """
        logger.info("Performing Chatterbox TTS synthesis...")

        try:
            # Use Chatterbox TTS with voice cloning if audio prompt provided
            if audio_prompt_path and os.path.exists(audio_prompt_path):
                logger.info(
                    f"Using voice cloning with audio prompt: {audio_prompt_path}"
                )
                audio_tensor = self.chatterbox.generate(
                    text=text,
                    audio_prompt_path=audio_prompt_path,
                    exaggeration=exaggeration,
                    cfg_weight=cfg_weight,
                )
            else:
                logger.info("Using default Chatterbox voice")
                audio_tensor = self.chatterbox.generate(
                    text=text, exaggeration=exaggeration, cfg_weight=cfg_weight
                )

            # Convert tensor to numpy array
            if hasattr(audio_tensor, "cpu"):
                audio_data = audio_tensor.cpu().numpy()
            else:
                audio_data = np.array(audio_tensor)

            # Ensure it's the right shape and type
            if len(audio_data.shape) > 1:
                audio_data = audio_data.squeeze()

            sample_rate = self.chatterbox.sr  # Chatterbox's sample rate

            return audio_data.astype(np.float32), sample_rate

        except Exception as e:
            logger.error(f"Chatterbox TTS synthesis failed: {e}")
            raise

    async def _save_audio_file(
        self, file_id: str, audio_data: np.ndarray, sample_rate: int, format: str
    ) -> str:
        """Save audio data to file"""
        file_path = os.path.join(self.temp_dir, f"{file_id}.{format}")

        # Save using soundfile
        sf.write(file_path, audio_data, sample_rate, format=format.upper())

        logger.info(f"Audio saved: {file_path}")
        return file_path

    async def get_audio_file(self, file_id: str) -> Optional[str]:
        """Get audio file path by ID"""
        return self.audio_files.get(file_id)

    async def delete_audio_file(self, file_id: str) -> bool:
        """Delete audio file by ID"""
        if file_id not in self.audio_files:
            return False

        try:
            file_path = self.audio_files[file_id]
            if os.path.exists(file_path):
                os.remove(file_path)

            del self.audio_files[file_id]
            logger.info(f"Deleted audio file: {file_id}")
            return True

        except Exception as e:
            logger.error(f"Failed to delete audio file {file_id}: {e}")
            return False

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
        if not await self.is_ready():
            raise RuntimeError("TTS service not initialized")

        if voice_name in self.cloned_voices:
            raise ValueError(f"Voice '{voice_name}' already exists")

        try:
            # Save the uploaded audio file
            audio_filename = f"{voice_name}.wav"
            audio_file_path = os.path.join(self.voices_dir, audio_filename)

            # Read and save the file
            content = await audio_file.read()
            with open(audio_file_path, "wb") as f:
                f.write(content)

            # Convert to WAV if needed (using soundfile)
            if not audio_file.filename.lower().endswith(".wav"):
                try:
                    # Read the audio file and convert to WAV
                    audio_data, sample_rate = sf.read(audio_file_path)
                    sf.write(audio_file_path, audio_data, sample_rate, format="WAV")
                    logger.info(f"Converted {audio_file.filename} to WAV format")
                except Exception as e:
                    logger.warning(f"Failed to convert audio format: {e}")

            # Create voice info
            voice_info = {
                "voice_name": voice_name,
                "description": description
                or f"Cloned voice from {audio_file.filename}",
                "audio_file_path": audio_file_path,
                "is_cloned": True,
                "created_at": datetime.now().isoformat(),
            }

            # Store the voice
            self.cloned_voices[voice_name] = voice_info

            logger.info(
                f"Voice '{voice_name}' cloned successfully from {audio_file.filename}"
            )

            return voice_info

        except Exception as e:
            # Clean up on failure
            if "audio_file_path" in locals() and os.path.exists(audio_file_path):
                os.remove(audio_file_path)
            raise

    async def get_cloned_voices(self) -> List[Dict]:
        """Get list of cloned voices only"""
        return [
            {
                "voice_name": voice_name,
                "description": voice_info.get("description"),
                "audio_file_path": voice_info.get("audio_file_path"),
                "is_cloned": True,
                "created_at": voice_info.get("created_at"),
            }
            for voice_name, voice_info in self.cloned_voices.items()
        ]

    async def delete_cloned_voice(self, voice_name: str) -> bool:
        """Delete a cloned voice"""
        if voice_name not in self.cloned_voices:
            return False

        try:
            # Remove the audio file
            voice_info = self.cloned_voices[voice_name]
            audio_file_path = voice_info.get("audio_file_path")

            if audio_file_path and os.path.exists(audio_file_path):
                os.remove(audio_file_path)
                logger.info(f"Removed audio file: {audio_file_path}")

            # Remove from memory
            del self.cloned_voices[voice_name]

            logger.info(f"Deleted cloned voice: {voice_name}")
            return True

        except Exception as e:
            logger.error(f"Failed to delete cloned voice {voice_name}: {e}")
            return False

    async def get_voice_sample_file(self, voice_name: str) -> Optional[str]:
        """Get the sample audio file path for a cloned voice"""
        if voice_name not in self.cloned_voices:
            return None

        return self.cloned_voices[voice_name].get("audio_file_path")

    async def cleanup(self):
        """Cleanup resources"""
        logger.info("Cleaning up TTS service...")

        # Delete all audio files
        for file_id in list(self.audio_files.keys()):
            await self.delete_audio_file(file_id)

        # Clean up cloned voices
        for voice_name in list(self.cloned_voices.keys()):
            await self.delete_cloned_voice(voice_name)

        # Remove temp directory
        if self.temp_dir and os.path.exists(self.temp_dir):
            try:
                import shutil

                shutil.rmtree(self.temp_dir)
                logger.info(f"Removed temp directory: {self.temp_dir}")
            except Exception as e:
                logger.warning(f"Failed to remove temp directory: {e}")

        self.is_initialized = False
        logger.info("TTS service cleanup completed")
