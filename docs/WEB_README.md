# Multi TTS Synthesizer Web Application

A web-based interface for the Multi TTS Synthesizer that provides the same functionality as the original desktop application, but accessible through a web browser from any computer on the network.

## Features

- **Multi-Engine Support**: Includes XTTSv2, Piper, Bark, and ElevenLabs text-to-speech engines
- **Web-Based Interface**: Accessible from any device with a web browser
- **Audio Library**: Manage and play generated audio files
- **Voice Customization**: Upload speaker samples for XTTSv2, choose from various voices for other engines
- **ElevenLabs Integration**: API key management and voice selection

## Requirements

- Python 3.8 or higher
- Dependencies listed in `web_requirements.txt`
- Optional: CUDA-capable GPU for faster synthesis (especially for XTTSv2 and Bark)

## Project Structure

```
multi-tts-web/
├── web_app.py                  # Main web application file
├── templates/                  # HTML templates
│   └── index.html              # Main interface template
├── api/                        # API modules
│   ├── tts_api.py              # API wrapper for TTS engines
│   └── rest_api_server.py      # REST API server (if needed)
├── tts_engines/                # TTS engine implementations
│   ├── __init__.py
│   ├── xtts_engine.py          # XTTSv2 implementation
│   ├── piper_engine.py         # Piper implementation
│   ├── bark_engine.py          # Bark implementation
│   └── elevenlabs_engine.py    # ElevenLabs implementation
├── audio_output/               # Directory for generated audio files
├── web_uploads/                # Directory for temporary uploads
├── speaker_samples/            # Directory for XTTS speaker samples
└── models/                     # Directory for model files
    └── piper/                  # Piper model files
```

## Setup

1. **Clone the Repository**:
   ```bash
   git clone https://github.com/yourusername/multi-tts-web.git
   cd multi-tts-web
   ```

2. **Install Dependencies**:
   ```bash
   pip install -r web_requirements.txt
   ```

3. **Model Setup**:
   - **XTTSv2**: Will be automatically downloaded on first use
   - **Piper**: Download the `.onnx` and `.onnx.json` model files from [Hugging Face - Piper Voices](https://huggingface.co/rhasspy/piper-voices/tree/main) and place them in the `models/piper/` directory
   - **Bark**: Will be automatically downloaded on first use
   - **ElevenLabs**: Requires an API key (free or paid account)

4. **Environment Variables** (optional for ElevenLabs):
   Create a `.env` file in the project root:
   ```
   ELEVENLABS_API_KEY_NAME1=your_api_key_here
   ELEVENLABS_API_KEY_NAME2=another_api_key_here
   FLASK_SECRET_KEY=your_secret_key_here
   ```

5. **Create Required Directories**:
   ```bash
   mkdir -p audio_output web_uploads speaker_samples models/piper
   ```

## Usage

1. **Start the Web Server**:
   ```bash
   python web_app.py
   ```
   The server will start on `http://0.0.0.0:5000` by default.

2. **Access the Web Interface**:
   Open a web browser and navigate to:
   - On the same computer: `http://localhost:5000`
   - From another computer: `http://[server-ip-address]:5000`

3. **Using the Interface**:
   - Select a TTS engine from the dropdown
   - Configure the engine-specific parameters
   - Enter the text you want to synthesize
   - Click "Start Synthesis"
   - Once complete, the audio will appear in the list and can be played directly in the browser

## Notes on GPU Acceleration

- For optimal performance with XTTSv2 and Bark, a CUDA-capable GPU is highly recommended
- The application will automatically use CUDA if available, falling back to CPU if not
- Synthesis on CPU can be very slow, especially for Bark

## Custom Speaker Samples (for XTTSv2)

For voice cloning with XTTSv2, you can:
1. Upload a WAV file directly through the web interface
2. Place WAV files in the `speaker_samples/` directory for reuse

Ideal speaker samples are 10-30 seconds of clear speech from a single speaker.

## Troubleshooting

- **Slow Synthesis**: Check if GPU acceleration is working correctly
- **Model Loading Errors**: Ensure you have sufficient disk space for model downloads
- **Audio Playback Issues**: Check that the audio format is supported by your browser
- **Network Access Problems**: Confirm the server is running and your firewall allows connections on the specified port