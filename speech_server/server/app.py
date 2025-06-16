from fastapi import FastAPI, HTTPException, UploadFile, File, Form, Request
from fastapi.responses import FileResponse, StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from pathlib import Path
from contextlib import asynccontextmanager
from typing import Optional, List

from speech_server.server.config import TTSServerConfig
from speech_server.server.models import (
    HealthResponse,
    TTSRequest,
    TTSResponse,
    VoiceInfo,
)


logger = None
tts_service = None


def create_app(config: TTSServerConfig) -> FastAPI:
    global logger
    from speech_server.server.logger import setup_logger

    print(config)

    logger = setup_logger(__name__)

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        global tts_service
        logger.info(f"Starting {config.title}...")
        logger.info(config)

        try:
            tts_service = config.service_factory()
            await tts_service.initialize()
            logger.info("TTS service initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize TTS service: {e}")
            raise

        yield

        logger.info(f"Shutting down {config.title}...")
        if tts_service:
            await tts_service.cleanup()

    app = FastAPI(
        title=config.title,
        version=config.version,
        description=config.description,
        docs_url="/docs",
        redoc_url="/redoc",
        lifespan=lifespan,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=config.allow_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    register_routes(app)
    return app


def register_routes(app: FastAPI):
    @app.get("/", response_model=HealthResponse)
    async def root():
        return HealthResponse(status="healthy", service=app.title, version=app.version)

    @app.get("/health", response_model=HealthResponse)
    async def health_check():
        try:
            is_ready = await tts_service.is_ready()
            return HealthResponse(
                status="healthy" if is_ready else "unhealthy",
                service=app.title,
                version=app.version,
            )
        except Exception as e:
            logger.error(f"Health check failed: {e}")
            raise HTTPException(status_code=503, detail="Service unhealthy")

    @app.get("/voices", response_model=List[VoiceInfo])
    async def list_voices():
        try:
            return await tts_service.get_available_voices()
        except Exception as e:
            logger.error(f"Failed to get voices: {e}")
            raise HTTPException(status_code=500, detail="Failed to retrieve voices")

    @app.post("/voices/clone", response_model=VoiceInfo)
    async def clone_voice(
        voice_name: str = Form(...),
        description: Optional[str] = Form(None),
        audio_file: UploadFile = File(...),
    ):
        try:
            if not audio_file.filename.lower().endswith((".wav", ".mp3", ".flac")):
                raise HTTPException(status_code=400, detail="Unsupported file format")

            return await tts_service.clone_voice(
                voice_name=voice_name,
                audio_file=audio_file,
                description=description,
            )
        except Exception as e:
            logger.error(f"Voice cloning failed: {e}")
            raise HTTPException(status_code=500, detail=str(e))

    @app.get("/voices/cloned", response_model=List[VoiceInfo])
    async def list_cloned_voices():
        try:
            return await tts_service.get_cloned_voices()
        except Exception as e:
            logger.error(f"Failed to get cloned voices: {e}")
            raise HTTPException(
                status_code=500, detail="Failed to retrieve cloned voices"
            )

    @app.delete("/voices/{voice_name}")
    async def delete_cloned_voice(voice_name: str):
        try:
            success = await tts_service.delete_cloned_voice(voice_name)
            if not success:
                raise HTTPException(status_code=404, detail="Voice not found")
            return {"message": f"Voice '{voice_name}' deleted successfully"}
        except Exception as e:
            logger.error(f"Failed to delete voice: {e}")
            raise HTTPException(status_code=500, detail="Failed to delete voice")

    @app.get("/voices/{voice_name}/sample")
    async def get_voice_sample(voice_name: str):
        try:
            path = await tts_service.get_voice_sample_file(voice_name)
            if not path or not Path(path).exists():
                raise HTTPException(status_code=404, detail="Sample not found")
            return FileResponse(path=path, media_type="audio/wav")
        except Exception as e:
            logger.error(f"Failed to retrieve voice sample: {e}")
            raise HTTPException(
                status_code=500, detail="Failed to retrieve voice sample"
            )

    @app.post("/synthesize")
    async def synthesize_text(request: Request, payload: TTSRequest):
        try:
            stream = tts_service.synthesize_stream(
                text=payload.text,
                voice_name=payload.voice_name,
                audio_prompt_path=payload.audio_prompt_path,
                exaggeration=payload.exaggeration,
                cfg_weight=payload.cfg_weight,
                output_format=payload.output_format,
            )
            return StreamingResponse(stream, media_type="audio/wav")
        except Exception as e:
            logger.error(f"Streaming failed: {e}")
            raise HTTPException(status_code=500, detail="Streaming failed.")

    @app.get("/audio/{audio_file_id}")
    async def get_audio(audio_file_id: str):
        try:
            path = await tts_service.get_audio_file(audio_file_id)
            if not path or not Path(path).exists():
                raise HTTPException(status_code=404, detail="Audio file not found")
            return FileResponse(path=path, media_type="audio/wav")
        except Exception as e:
            logger.error(f"Failed to retrieve audio file: {e}")
            raise HTTPException(status_code=500, detail="Failed to retrieve audio file")

    @app.post("/synthesize-file", response_model=TTSResponse)
    async def synthesize_file(
        file: UploadFile = File(...),
        voice_name: Optional[str] = Form(None),
        exaggeration: Optional[float] = Form(0.5),
        cfg_weight: Optional[float] = Form(0.5),
        speed: Optional[float] = Form(1.0),
        output_format: Optional[str] = Form("wav"),
    ):
        try:
            content = await file.read()
            text = content.decode("utf-8")
            if len(text) > 5000:
                raise HTTPException(status_code=400, detail="Text too long")

            audio_file_id, duration = await tts_service.synthesize(
                text=text,
                voice_name=voice_name,
                speed=speed,
                exaggeration=exaggeration,
                cfg_weight=cfg_weight,
                output_format=output_format,
            )
            return TTSResponse(
                message="Synthesis successful",
                audio_file_id=audio_file_id,
                duration=duration,
            )
        except Exception as e:
            logger.error(f"File synthesis failed: {e}")
            raise HTTPException(status_code=500, detail=str(e))

    @app.delete("/audio/{audio_file_id}")
    async def delete_audio(audio_file_id: str):
        try:
            success = await tts_service.delete_audio_file(audio_file_id)
            if not success:
                raise HTTPException(status_code=404, detail="Audio file not found")
            return {"message": "Audio file deleted successfully"}
        except Exception as e:
            logger.error(f"Failed to delete audio file: {e}")
            raise HTTPException(status_code=500, detail="Failed to delete audio file")
