# Chatterbox TTS API

## TODO:
- [] Add streaming
- [] Add more voices


A FastAPI wrapper around [Chatterbox TTS](https://github.com/resemble-ai/chatterbox) for text-to-speech synthesis.

## Features

- 🚀 FastAPI-based REST API
- 🎵 Multiple voice support
- 📁 File upload synthesis
- 🎛️ Configurable speech parameters (speed, format)
- 📊 Rich logging with beautiful console output
- 🔧 Built with Poetry and pyenv
- 📖 Auto-generated OpenAPI documentation

## Prerequisites

- Python 3.9+
- [pyenv](https://github.com/pyenv/pyenv) for Python version management
- [Poetry](https://python-poetry.org/) for dependency management

## Installation

1. **Clone the repository:**
   ```bash
   git clone <your-repo-url>
   cd chatterbox-tts-api
   ```

2. **Set up Python version with pyenv:**
   ```bash
   pyenv install 3.9.18
   pyenv local 3.9.18
   ```

3. **Install dependencies with Poetry:**
   ```bash
   poetry install
   ```

4. **Install Chatterbox TTS:**
   ```bash
   poetry shell
   pip install git+https://github.com/resemble-ai/chatterbox.git
   ```

## Usage

### Running the API

1. **Activate the Poetry environment:**
   ```bash
   poetry shell
   ```

2. **Start the development server:**
   ```bash
   uvicorn chatterbox_tts_api.server:app --reload --host 0.0.0.0 --port 8000
   ```

   Or run directly:
   ```bash
   python -m chatterbox_tts_api.server
   ```

3. **Access the API:**
   - API: http://localhost:8000
   - Documentation: http://localhost:8000/docs
   - ReDoc: http://localhost:8000/redoc

### API Endpoints

#### Health Check
```bash
GET /health
```

#### List Available Voices
```bash
GET /voices
```

#### Synthesize Text
```bash
POST /synthesize
Content-Type: application/json

{
  "text": "Hello, world!",
  "voice_name": "default",
  "speed": 1.0,
  "output_format": "wav"
}
```

#### Upload and Synthesize File
```bash
POST /synthesize-file
Content-Type: multipart/form-data

file: <text-file>
voice_name: "default"
speed: 1.0
output_format: "wav"
```

#### Download Audio
```bash
GET /audio/{audio_file_id}
```

#### Delete Audio
```bash
DELETE /audio/{audio_file_id}
```

### Example Usage with curl

```bash
# Synthesize text
curl -X POST "http://localhost:8000/synthesize" \
  -H "Content-Type: application/json" \
  -d '{
    "text": "Hello, this is a test of the Chatterbox TTS API!",
    "voice_name": "default",
    "speed": 1.0
  }'

# Download the generated audio
curl -X GET "http://localhost:8000/audio/{file_id}" \
  -o "output.wav"
```

### Python Client Example

```python
import httpx
import asyncio

async def synthesize_text():
    async with httpx.AsyncClient() as client:
        # Synthesize text
        response = await client.post(
            "http://localhost:8000/synthesize",
            json={
                "text": "Hello from Python!",
                "voice_name": "default",
                "speed": 1.2
            }
        )
        
        result = response.json()
        file_id = result["audio_file_id"]
        
        # Download audio
        audio_response = await client.get(f"http://localhost:8000/audio/{file_id}")
        
        with open("output.wav", "wb") as f:
            f.write(audio_response.content)
        
        print(f"Audio saved as output.wav (Duration: {result['duration']}s)")

# Run the example
asyncio.run(synthesize_text())
```

## Development

### Code Formatting

```bash
# Format code with black
poetry run black src/

# Sort imports with isort
poetry run isort src/

# Lint with flake8
poetry run flake8 src/
```

### Type Checking

```bash
poetry run mypy src/
```

### Testing

```bash
poetry run pytest
```

## Configuration

### Environment Variables

- `CHATTERBOX_MODEL_PATH`: Path to Chatterbox TTS model files
- `TTS_TEMP_DIR`: Directory for temporary audio files
- `LOG_LEVEL`: Logging level (DEBUG, INFO, WARNING, ERROR)

### Logging

The API uses Rich for beautiful console logging with:
- Colored output
- Timestamps
- File paths with links
- Rich tracebacks
- Request/response logging

## Chatterbox TTS Integration

**Note:** The current implementation includes a mock TTS service for demonstration. To integrate with actual Chatterbox TTS:

1. Replace the mock implementation in `src/chatterbox_tts_api/tts_service.py`
2. Update the `_initialize_model()` method to load the actual Chatterbox TTS model
3. Implement the `_synthes