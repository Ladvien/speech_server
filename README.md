# 🗣️ Speech Server – TTS API with Chatterbox & Kokoro

<!-- start intro -->
This project provides a FastAPI-based HTTP server for generating speech audio using [Chatterbox TTS](https://github.com/chatterbox-voice/chatterbox-tts) or [Kokoro ONNX](https://huggingface.co/kokoro-ai).
<!-- end intro -->

---

<!-- start quick_start -->
## 🚀 Quick Start

### 1. Clone the Repo

```bash
git clone https://github.com/Ladvien/speech_server.git
cd speech_server
```

### 2. Install Dependencies

We use [Poetry](https://python-poetry.org/) for managing dependencies.

```bash
poetry install
```

### 3. Run the Server

```bash
poetry run speech-server
```

Or:

```bash
poetry run uvicorn speech_server.server.app:app --host 0.0.0.0 --port 8000
```

Access:

- API: http://localhost:8000
- Docs: http://localhost:8000/docs
<!-- end quick_start -->

---

<!-- start usage -->
## 🧪 Example Usage

### Generate Audio from Text

```bash
curl -X POST http://localhost:8000/tts \
     -H "Content-Type: application/json" \
     -d '{"text": "Hello, world!", "voice": "default"}' \
     --output hello.wav
```

### List Voices

```bash
curl http://localhost:8000/voices
```
<!-- end usage -->

---

<!-- start config -->
## ⚙️ Configuration

Use `config.yaml`, environment variables, or Python config classes like `TTSServerConfig`.

```yaml
tts_service: chatterbox  # or 'kokoro'
voice: default
log_level: info
sample_rate: 24000
```
<!-- end config -->

---

<!-- start features -->
## 🧠 Features

- ✅ Chatterbox TTS (PyTorch)
- ✅ Kokoro ONNX (lightweight, GPU-ready)
- ✅ Voice cloning support
- ✅ Streaming endpoint
- ✅ `/voices` API
- ✅ YAML config support
- ✅ Ready for Docker or cloud deployment
<!-- end features -->

---

<!-- start extension -->
## 🧩 Extend It

To add a new TTS engine, subclass:

```
speech_server.common.base_tts_service.TTSService
```

Then register it via your config loader.
<!-- end extension -->

---

<!-- start dev -->
## 🛠 Dev Tools

### Lint, Format, Test

```bash
poetry run black .
poetry run isort .
poetry run pytest
```

### Type Check

```bash
poetry run mypy src/
```
<!-- end dev -->

---

<!-- start docs -->
## 📚 Documentation

Build local docs:

```bash
cd docs
make html
```

Docs live in `/docs/source/` and are rendered via [ReadTheDocs](https://readthedocs.org/).
<!-- end docs -->

---

<!-- start license -->
## 📄 License

MIT © C. Thomas Brittain
<!-- end license -->
