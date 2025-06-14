"""
Chatterbox TTS API - FastAPI wrapper for Chatterbox TTS
"""

__version__ = "0.1.0"
__author__ = "Your Name"
__email__ = "your.email@example.com"

from .server import app
from .tts_service import ChatterboxTTSService
from .logger import get_logger, setup_logger

__all__ = ["app", "ChatterboxTTSService", "get_logger", "setup_logger"]
