"""
FastAPI wrapper for Chatterbox TTS
"""

from typing import Optional

from pydantic import BaseModel, Field


class TTSRequest(BaseModel):
    text: str = Field(..., description="Text to synthesize", max_length=5000)
    voice_name: Optional[str] = Field(None, description="Voice name to use")
    audio_prompt_path: Optional[str] = Field(
        None, description="[Chatterbox only] Path to audio prompt for voice cloning"
    )
    speed: Optional[float] = Field(
        1.0, description="Speech speed multiplier", ge=0.1, le=3.0
    )
    exaggeration: Optional[float] = Field(
        0.5,
        description="[Chatterbox only] Emotion exaggeration control",
        ge=0.0,
        le=2.0,
    )
    cfg_weight: Optional[float] = Field(
        0.5,
        description="[Chatterbox only] CFG weight for generation control",
        ge=0.0,
        le=1.0,
    )
    output_format: Optional[str] = Field("wav", description="Output audio format")


class TTSResponse(BaseModel):
    message: str
    audio_file_id: str
    duration: Optional[float] = None


class VoiceCloneRequest(BaseModel):
    voice_name: str = Field(
        ..., description="Name for the cloned voice (Chatterbox only)"
    )
    description: Optional[str] = Field(None, description="Description of the voice")


# TODO: Split voice into per model. Kokoro requires it, chatterbox does not.
class VoiceInfo(BaseModel):
    name: Optional[str] = None  # Chatterbox
    voice_name: Optional[str] = None  # Chatterbox
    description: Optional[str] = None
    audio_file_path: Optional[str] = None
    is_cloned: Optional[bool] = None
    created_at: Optional[str] = None


class HealthResponse(BaseModel):
    status: str
    service: str
    version: str
