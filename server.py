#!/usr/bin/env python3
"""
Script to run the Chatterbox TTS API server
"""
import sys
import os

# Add the src directory to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "chatterbox_tts_api"))

if __name__ == "__main__":
    import uvicorn

    # Run the server
    uvicorn.run(
        "chatterbox_tts_api.server:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_config=None,
    )
