from dataclasses import dataclass
from typing import Callable, List
from speech_server.common.base_tts_service import TTSService


@dataclass
class TTSServerConfig:
    service_factory: Callable[[], TTSService]
    allow_origins: List[str]
    title: str
    version: str
    description: str
