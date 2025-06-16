from chatterbox_tts_api.tts_services.kokoro_tts_service import (
    KokoroTTSService,
    KokoroTTSServiceConfig,
    KokoroPipelineConfig,
    KokoroResponseConfig,
)
from chatterbox_tts_api.server.config import TTSServerConfig
from chatterbox_tts_api.server.app import create_app

# ✅ Define Kokoro-specific runtime configuration
kokoro_config = KokoroTTSServiceConfig(
    model_name="kokoro-v1.0.fp16-gpu.onnx",
    pipeline=KokoroPipelineConfig(
        voice="af_bella",
        language_code="en-us",
        speed=1.0,
    ),
    response=KokoroResponseConfig(
        format="wav",
        sample_rate=24000,
        channels=1,
    ),
    base_download_link="https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.0",
    model_filenames=[
        "kokoro-v1.0.fp16-gpu.onnx",
        "kokoro-v1.0.fp16.onnx",
        "kokoro-v1.0.int8.onnx",
        "kokoro-v1.0.onnx",
    ],
    voices_filenames=[
        "voices-v1.0.bin",
    ],
)

# ✅ Wrap config in server app config
config = TTSServerConfig(
    service_factory=lambda: KokoroTTSService(config=kokoro_config),
    allow_origins=["*"],
    title="Kokoro TTS API",
    version="0.1.0",
    description="Kokoro ONNX TTS Engine",
)

app = create_app(config)

if __name__ == "__main__":
    import uvicorn

    uvicorn.run("server:app", host="0.0.0.0", port=8000, reload=True)
