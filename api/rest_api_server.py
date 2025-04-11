# rest_api_server.py
"""
REST API server for the Multi TTS Synthesizer.

This script creates a FastAPI server that exposes the TTS functionality
over HTTP, allowing remote applications to use the services.

Requirements:
    pip install fastapi uvicorn python-multipart

Usage:
    uvicorn rest_api_server:app --host 0.0.0.0 --port 8000
"""

import os
import base64
import logging
from typing import List, Dict, Optional, Any
from fastapi import FastAPI, File, UploadFile, Form, HTTPException, BackgroundTasks
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field
import uvicorn
import uuid
from tts_api import MultiTTSAPI
from tts_engines import elevenlabs_engine

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - [REST-API] %(message)s'
)
logger = logging.getLogger('rest_api')

# Create API instance
api = MultiTTSAPI()

# Create FastAPI app
app = FastAPI(
    title="Multi TTS Synthesizer API",
    description="REST API for synthesizing text to speech using multiple engines",
    version="1.0.0"
)

# Temporary directory for files
TEMP_DIR = "api_temp_files"
os.makedirs(TEMP_DIR, exist_ok=True)

# Directory for output files
OUTPUT_DIR = "api_output"
os.makedirs(OUTPUT_DIR, exist_ok=True)


# --- Pydantic Models ---

class XTTSRequest(BaseModel):
    text: str = Field(..., description="Text to synthesize")
    language: str = Field("en", description="Language code (e.g., en, nl, fr)")
    speaker_wav_base64: Optional[str] = Field(None, description="Optional base64-encoded speaker WAV file")


class PiperRequest(BaseModel):
    text: str = Field(..., description="Text to synthesize")
    model_name: str = Field(..., description="Name of the Piper model to use (e.g., en_US-lessac-medium)")


class BarkRequest(BaseModel):
    text: str = Field(..., description="Text to synthesize")
    voice_preset: str = Field("v2/en_speaker_6", description="Voice preset to use")
    model_name: str = Field("suno/bark-small", description="Model name")


class ElevenLabsRequest(BaseModel):
    text: str = Field(..., description="Text to synthesize")
    voice_id: str = Field(..., description="Voice ID to use")
    model_id: str = Field("eleven_multilingual_v2", description="Model ID to use")
    api_key: str = Field(..., description="ElevenLabs API key")


class ElevenLabsVoiceRequest(BaseModel):
    api_key: str = Field(..., description="ElevenLabs API key")


class SuccessResponse(BaseModel):
    success: bool
    message: str
    file_url: Optional[str] = None


class ErrorResponse(BaseModel):
    success: bool = False
    error: str


class InfoResponse(BaseModel):
    engines: List[str]
    bark_voices: List[str]
    elevenlabs_models: List[str]


class VoicesResponse(BaseModel):
    voices: List[Dict[str, str]]


# --- Helper Functions ---

def get_temp_path(prefix: str, suffix: str) -> str:
    """Generate a unique temporary file path."""
    unique_id = str(uuid.uuid4())
    return os.path.join(TEMP_DIR, f"{prefix}_{unique_id}{suffix}")


def get_output_path(prefix: str) -> str:
    """Generate a unique output file path."""
    unique_id = str(uuid.uuid4())
    return os.path.join(OUTPUT_DIR, f"{prefix}_{unique_id}.wav")


def cleanup_file(file_path: str) -> None:
    """Delete a temporary file."""
    try:
        if os.path.exists(file_path):
            os.remove(file_path)
            logger.info(f"Deleted temporary file: {file_path}")
    except Exception as e:
        logger.error(f"Error deleting file {file_path}: {e}")


# --- API Routes ---

@app.get("/", tags=["Info"])
async def root():
    """Root endpoint with API information."""
    return {
        "name": "Multi TTS Synthesizer API",
        "version": "1.0.0",
        "documentation": "/docs",
        "endpoints": {
            "GET /info": "Get information about available engines and voices",
            "POST /synthesize/xtts": "Synthesize text using XTTSv2",
            "POST /synthesize/piper": "Synthesize text using Piper",
            "POST /synthesize/bark": "Synthesize text using Bark",
            "POST /synthesize/elevenlabs": "Synthesize text using ElevenLabs",
            "POST /elevenlabs/voices": "Get available ElevenLabs voices"
        }
    }


@app.get("/info", response_model=InfoResponse, tags=["Info"])
async def get_info():
    """Get information about available engines and voices."""
    return {
        "engines": ["xtts", "piper", "bark", "elevenlabs"],
        "bark_voices": api.default_bark_voices,
        "elevenlabs_models": list(elevenlabs_engine.ELEVENLABS_MODELS)
    }


@app.post("/synthesize/xtts", response_model=SuccessResponse, responses={400: {"model": ErrorResponse}},
          tags=["Synthesis"])
async def synthesize_xtts(request: XTTSRequest, background_tasks: BackgroundTasks):
    """
    Synthesize text using XTTSv2.

    Optionally provide a base64-encoded speaker WAV file for voice cloning.
    """
    speaker_wav_path = None

    try:
        # Handle optional speaker WAV
        if request.speaker_wav_base64:
            try:
                wav_data = base64.b64decode(request.speaker_wav_base64)
                speaker_wav_path = get_temp_path("speaker", ".wav")

                with open(speaker_wav_path, "wb") as f:
                    f.write(wav_data)

                logger.info(f"Saved speaker WAV to {speaker_wav_path}")
                # Schedule cleanup
                background_tasks.add_task(cleanup_file, speaker_wav_path)
            except Exception as e:
                raise HTTPException(status_code=400, detail=f"Invalid speaker WAV data: {e}")

        # Generate a unique output path
        output_path = get_output_path("xtts")

        # Call the API
        success, message = api.synthesize_xtts(
            text=request.text,
            language=request.language,
            speaker_wav_path=speaker_wav_path,
            output_path=output_path
        )

        if not success:
            raise HTTPException(status_code=400, detail=message)

        # Build response with file URL
        file_url = f"/download/{os.path.basename(output_path)}"
        return {
            "success": True,
            "message": message,
            "file_url": file_url
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in xtts synthesis: {e}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {e}")


@app.post("/synthesize/piper", response_model=SuccessResponse, responses={400: {"model": ErrorResponse}},
          tags=["Synthesis"])
async def synthesize_piper(request: PiperRequest):
    """
    Synthesize text using Piper.

    Specify a model name from the available Piper models.
    """
    try:
        # Check if the model exists
        model_base = os.path.join(api.DEFAULT_PIPER_MODEL_DIR, request.model_name)
        onnx_path = f"{model_base}.onnx"
        json_path = f"{model_base}.onnx.json"

        if not os.path.exists(onnx_path):
            raise HTTPException(status_code=400, detail=f"Piper model not found: {onnx_path}")
        if not os.path.exists(json_path):
            raise HTTPException(status_code=400, detail=f"Piper config not found: {json_path}")

        # Generate a unique output path
        output_path = get_output_path("piper")

        # Call the API
        success, message = api.synthesize_piper(
            text=request.text,
            model_onnx_path=onnx_path,
            model_json_path=json_path,
            output_path=output_path
        )

        if not success:
            raise HTTPException(status_code=400, detail=message)

        # Build response with file URL
        file_url = f"/download/{os.path.basename(output_path)}"
        return {
            "success": True,
            "message": message,
            "file_url": file_url
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in piper synthesis: {e}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {e}")


@app.post("/synthesize/bark", response_model=SuccessResponse, responses={400: {"model": ErrorResponse}},
          tags=["Synthesis"])
async def synthesize_bark(request: BarkRequest):
    """
    Synthesize text using Bark.

    Specify a voice preset from the available list.
    """
    try:
        # Generate a unique output path
        output_path = get_output_path("bark")

        # Call the API
        success, message = api.synthesize_bark(
            text=request.text,
            voice_preset=request.voice_preset,
            model_name=request.model_name,
            output_path=output_path
        )

        if not success:
            raise HTTPException(status_code=400, detail=message)

        # Build response with file URL
        file_url = f"/download/{os.path.basename(output_path)}"
        return {
            "success": True,
            "message": message,
            "file_url": file_url
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in bark synthesis: {e}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {e}")


@app.post("/synthesize/elevenlabs", response_model=SuccessResponse, responses={400: {"model": ErrorResponse}}, tags=["Synthesis"])
async def synthesize_elevenlabs(request: ElevenLabsRequest):
    """
    Synthesize text using ElevenLabs.

    Requires a valid ElevenLabs API key, voice ID, and model ID.
    """
    try:
        # First validate the API key
        if not api.validate_elevenlabs_key(request.api_key):
            raise HTTPException(status_code=400, detail="Invalid ElevenLabs API key")

        # Generate a unique output path
        output_path = get_output_path("elevenlabs")

        # Call the API
        success, message = api.synthesize_elevenlabs(
            text=request.text,
            voice_id=request.voice_id,
            model_id=request.model_id,
            output_path=output_path,
            api_key=request.api_key
        )

        if not success:
            raise HTTPException(status_code=400, detail=message)

        # Build response with file URL
        file_url = f"/download/{os.path.basename(output_path)}"
        return {
            "success": True,
            "message": message,
            "file_url": file_url
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in elevenlabs synthesis: {e}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {e}")

@app.post("/elevenlabs/voices", response_model=VoicesResponse, responses={400: {"model": ErrorResponse}}, tags=["ElevenLabs"])
async def get_elevenlabs_voices(request: ElevenLabsVoiceRequest):
    """
    Get available ElevenLabs voices.

    Requires a valid ElevenLabs API key.
    """
    try:
        # First validate the API key
        if not api.validate_elevenlabs_key(request.api_key):
            raise HTTPException(status_code=400, detail="Invalid ElevenLabs API key")

        # Get voices
        voices = api.get_elevenlabs_voices(request.api_key)

        # Format the response
        voice_list = [{"name": name, "id": voice_id} for name, voice_id in voices]
        return {"voices": voice_list}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching ElevenLabs voices: {e}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {e}")

@app.get("/download/{filename}", tags=["Download"])
async def download_file(filename: str):
    """
    Download a generated audio file.

    The filename should be obtained from a previous synthesis response.
    """
    file_path = os.path.join(OUTPUT_DIR, filename)

    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="File not found")

    return FileResponse(
        path=file_path,
        filename=filename,
        media_type="audio/wav"
    )

@app.post("/synthesize/xtts/upload", response_model=SuccessResponse, responses={400: {"model": ErrorResponse}}, tags=["Synthesis"])
async def synthesize_xtts_with_upload(
    text: str = Form(...),
    language: str = Form("en"),
    speaker_wav: Optional[UploadFile] = File(None),
    background_tasks: BackgroundTasks = None
):
    """
    Synthesize text using XTTSv2 with a file upload.

    Optionally upload a speaker WAV file for voice cloning.
    """
    speaker_wav_path = None

    try:
        # Handle speaker WAV upload
        if speaker_wav:
            try:
                speaker_wav_path = get_temp_path("speaker", ".wav")

                with open(speaker_wav_path, "wb") as f:
                    f.write(await speaker_wav.read())

                logger.info(f"Saved uploaded speaker WAV to {speaker_wav_path}")
                # Schedule cleanup
                if background_tasks:
                    background_tasks.add_task(cleanup_file, speaker_wav_path)
            except Exception as e:
                raise HTTPException(status_code=400, detail=f"Error processing uploaded WAV: {e}")

        # Generate a unique output path
        output_path = get_output_path("xtts")

        # Call the API
        success, message = api.synthesize_xtts(
            text=text,
            language=language,
            speaker_wav_path=speaker_wav_path,
            output_path=output_path
        )

        if not success:
            raise HTTPException(status_code=400, detail=message)

        # Build response with file URL
        file_url = f"/download/{os.path.basename(output_path)}"
        return {
            "success": True,
            "message": message,
            "file_url": file_url
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in xtts synthesis with upload: {e}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {e}")

@app.on_event("startup")
async def startup_event():
    """Initialize resources on startup."""
    logger.info("Starting Multi TTS API Server")

    # Ensure directories exist
    os.makedirs(TEMP_DIR, exist_ok=True)
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    # Cleanup any old temporary files
    try:
        for filename in os.listdir(TEMP_DIR):
            file_path = os.path.join(TEMP_DIR, filename)
            if os.path.isfile(file_path):
                os.remove(file_path)
        logger.info("Cleaned up temporary files")
    except Exception as e:
        logger.error(f"Error cleaning up temporary files: {e}")

@app.on_event("shutdown")
async def shutdown_event():
    """Clean up resources on shutdown."""
    logger.info("Shutting down Multi TTS API Server")

# --- Main Entry Point ---
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    host = os.environ.get("HOST", "0.0.0.0")

    print(f"\n--- Multi TTS API Server ---")
    print(f"Starting server on http://{host}:{port}")
    print(f"API documentation: http://{host}:{port}/docs")
    print(f"Alternative API docs: http://{host}:{port}/redoc")
    print(f"Press Ctrl+C to stop the server")

    uvicorn.run(app, host=host, port=port)