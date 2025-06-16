from dataclasses import dataclass, field
import os
from typing import List


@dataclass
class TTSBaseConfig:
    runtime_data_dir: str = field(
        default_factory=lambda: os.path.abspath("runtime_data")
    )
    default_voice: str = "default"
    sample_rate: int = 24000
    supported_formats: List[str] = field(default_factory=lambda: ["wav"])
