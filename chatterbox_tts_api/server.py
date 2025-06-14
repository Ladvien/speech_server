"""
FastAPI wrapper for Chatterbox TTS
"""
from pathlib import Path
from typing import Optional, List
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, UploadFile, File, Form
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware

from chatterbox_tts_api.models import HealthResponse, TTSRequest, TTSResponse, VoiceInfo

try:
    from .tts_service import ChatterboxTTSService
    from .logger import setup_logger
except ImportError:
    # Handle direct execution
    from tts_service import ChatterboxTTSService
    from logger import setup_logger

# Setup rich logging
logger = setup_logger(__name__)

# Initialize TTS service (will be set in lifespan)
tts_service = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager"""
    global tts_service

    # Startup
    logger.info("Starting Chatterbox TTS API...")
    try:
        tts_service = ChatterboxTTSService()
        await tts_service.initialize()
        logger.info("TTS service initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize TTS service: {e}")
        raise

    yield

    # Shutdown
    logger.info("Shutting down Chatterbox TTS API...")
    if tts_service:
        await tts_service.cleanup()


# Initialize FastAPI app with lifespan
app = FastAPI(
    title="Chatterbox TTS API",
    description="A FastAPI wrapper around Chatterbox TTS for text-to-speech synthesis",
    version="0.1.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure as needed for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/", response_model=HealthResponse)
async def root():
    """Health check endpoint"""
    return HealthResponse(
        status="healthy", service="Chatterbox TTS API", version="0.1.0"
    )


@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Detailed health check"""
    try:
        is_ready = await tts_service.is_ready()
        status = "healthy" if is_ready else "unhealthy"
        return HealthResponse(
            status=status, service="Chatterbox TTS API", version="0.1.0"
        )
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        raise HTTPException(status_code=503, detail="Service unhealthy")


@app.get("/voices", response_model=List[VoiceInfo])
async def list_voices():
    """Get available voices (both default and cloned)"""
    try:
        voices = await tts_service.get_available_voices()
        return voices
    except Exception as e:
        logger.error(f"Failed to get voices: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve voices")


@app.post("/voices/clone", response_model=VoiceInfo)
async def clone_voice(
    voice_name: str = Form(...),
    description: Optional[str] = Form(None),
    audio_file: UploadFile = File(
        ..., description="Audio file for voice cloning (.wav or .mp3)"
    ),
):
    """Clone a voice from an uploaded audio file"""
    try:
        # Validate file type
        if not audio_file.filename.lower().endswith((".wav", ".mp3", ".flac")):
            raise HTTPException(
                status_code=400, detail="Only .wav, .mp3, and .flac files are supported"
            )

        logger.info(f"Cloning voice '{voice_name}' from file: {audio_file.filename}")

        voice_info = await tts_service.clone_voice(
            voice_name=voice_name, audio_file=audio_file, description=description
        )

        logger.info(f"Voice '{voice_name}' cloned successfully")
        return voice_info

    except Exception as e:
        logger.error(f"Voice cloning failed: {e}")
        raise HTTPException(status_code=500, detail=f"Voice cloning failed: {str(e)}")


@app.get("/voices/cloned", response_model=List[VoiceInfo])
async def list_cloned_voices():
    """Get list of cloned voices"""
    try:
        voices = await tts_service.get_cloned_voices()
        return voices
    except Exception as e:
        logger.error(f"Failed to get cloned voices: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve cloned voices")


@app.delete("/voices/{voice_name}")
async def delete_cloned_voice(voice_name: str):
    """Delete a cloned voice"""
    try:
        success = await tts_service.delete_cloned_voice(voice_name)
        if not success:
            raise HTTPException(status_code=404, detail="Voice not found")

        return {"message": f"Voice '{voice_name}' deleted successfully"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete voice: {e}")
        raise HTTPException(status_code=500, detail="Failed to delete voice")


@app.get("/voices/{voice_name}/sample")
async def get_voice_sample(voice_name: str):
    """Download the sample audio file for a cloned voice"""
    try:
        file_path = await tts_service.get_voice_sample_file(voice_name)
        if not file_path or not Path(file_path).exists():
            raise HTTPException(status_code=404, detail="Voice sample not found")

        return FileResponse(
            path=file_path, media_type="audio/wav", filename=f"{voice_name}_sample.wav"
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to retrieve voice sample: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve voice sample")


@app.post("/synthesize", response_model=TTSResponse)
async def synthesize_text(request: TTSRequest):
    """Synthesize text to speech with optional voice cloning"""
    try:
        logger.info(
            f"Synthesizing text: '{request.text[:50]}...' with voice: {request.voice_name}"
        )

        audio_file_id, duration = await tts_service.synthesize(
            text=request.text,
            voice_name=request.voice_name,
            audio_prompt_path=request.audio_prompt_path,
            speed=request.speed,
            exaggeration=request.exaggeration,
            cfg_weight=request.cfg_weight,
            output_format=request.output_format,
        )

        logger.info(
            f"Synthesis completed. File ID: {audio_file_id}, Duration: {duration}s"
        )

        return TTSResponse(
            message="Text synthesized successfully",
            audio_file_id=audio_file_id,
            duration=duration,
        )
    except Exception as e:
        logger.error(f"Synthesis failed: {e}")
        raise HTTPException(status_code=500, detail=f"Synthesis failed: {str(e)}")


@app.get("/audio/{audio_file_id}")
async def get_audio(audio_file_id: str):
    """Download synthesized audio file"""
    try:
        file_path = await tts_service.get_audio_file(audio_file_id)
        if not file_path or not Path(file_path).exists():
            raise HTTPException(status_code=404, detail="Audio file not found")

        return FileResponse(
            path=file_path, media_type="audio/wav", filename=f"{audio_file_id}.wav"
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to retrieve audio file: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve audio file")


@app.post("/synthesize-file", response_model=TTSResponse)
async def synthesize_file(
    file: UploadFile = File(..., description="Text file to synthesize"),
    voice_name: Optional[str] = Form(None),
    exaggeration: Optional[float] = Form(0.5),
    cfg_weight: Optional[float] = Form(0.5),
    speed: Optional[float] = Form(1.0),
    output_format: Optional[str] = Form("wav"),
):
    """Synthesize text from uploaded file"""
    try:
        # Validate file type
        if not file.filename.endswith((".txt", ".md")):
            raise HTTPException(
                status_code=400, detail="Only .txt and .md files are supported"
            )

        # Read file content
        content = await file.read()
        text = content.decode("utf-8")

        if len(text) > 5000:
            raise HTTPException(
                status_code=400, detail="Text too long (max 5000 characters)"
            )

        logger.info(f"Synthesizing file: {file.filename} ({len(text)} characters)")

        audio_file_id, duration = await tts_service.synthesize(
            text=text,
            voice_name=voice_name,
            speed=speed,
            exaggeration=exaggeration,
            cfg_weight=cfg_weight,
            output_format=output_format,
        )

        return TTSResponse(
            message=f"File '{file.filename}' synthesized successfully",
            audio_file_id=audio_file_id,
            duration=duration,
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"File synthesis failed: {e}")
        raise HTTPException(status_code=500, detail=f"File synthesis failed: {str(e)}")


@app.delete("/audio/{audio_file_id}")
async def delete_audio(audio_file_id: str):
    """Delete synthesized audio file"""
    try:
        success = await tts_service.delete_audio_file(audio_file_id)
        if not success:
            raise HTTPException(status_code=404, detail="Audio file not found")

        return {"message": "Audio file deleted successfully"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete audio file: {e}")
        raise HTTPException(status_code=500, detail="Failed to delete audio file")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "chatterbox_tts_api.server:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_config=None,  # Use our custom logging
    )
