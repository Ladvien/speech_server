# === Kokoro TTS Config ===

from src import (
    create_app,
    TTSServerConfig,
    KokoroTTSServiceConfig,
    KokoroPipelineConfig,
    KokoroResponseConfig,
    KokoroTTSService,
    ChatterboxTTSServiceConfig,
    ChatterboxPipelineConfig,
    ChatterboxResponseConfig,
    ChatterboxTTSService,
)

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
    voices_filenames=["voices-v1.0.bin"],
)

chatterbox_config = ChatterboxTTSServiceConfig(
    pipeline=ChatterboxPipelineConfig(
        exaggeration=0.6,
        cfg_weight=0.7,
    ),
    response=ChatterboxResponseConfig(
        format="wav",
        sample_rate=24000,
        channels=1,
    ),
)

# # === Server App Config ===
# config = TTSServerConfig(
#     # Swap to Chatterbox by replacing this:
#     service_factory=lambda: KokoroTTSService(config=kokoro_config),
#     allow_origins=["*"],
#     title="Kokoro TTS API",
#     version="0.1.0",
#     description="Kokoro ONNX TTS Engine",
# )

config = TTSServerConfig(
    # Swap to Chatterbox by replacing this:
    service_factory=lambda: ChatterboxTTSService(config=chatterbox_config),
    allow_origins=["*"],
    title="Chatterbox TTS API",
    version="0.1.0",
    description="Chatterbox TTS Engine",
)


app = create_app(config)

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8888)
